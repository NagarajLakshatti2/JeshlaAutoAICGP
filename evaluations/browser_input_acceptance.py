"""Explicit browser entry/clear acceptance; no provider, Gradle, Jira or target edit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--case-file', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--by', choices=['label', 'placeholder', 'role'], required=True)
    parser.add_argument('--field', required=True)
    parser.add_argument('--value', required=True)
    parser.add_argument('--dismiss-button', help='Exact observed harmless overlay button name; no guessed automatic consent.')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    requested = urlparse(args.url)
    if requested.scheme != 'https' or not requested.hostname or requested.username or requested.password:
        parser.error('Use an explicit HTTPS test-page URL without credentials.')
    out = args.output_dir.resolve()
    if not out.is_relative_to(ROOT / 'outputs' / 'acceptance'):
        parser.error('Evidence must stay under outputs/acceptance.')
    raw = args.case_file.read_bytes()
    pack = json.loads(raw)
    selected = [c for c in pack.get('test_cases', pack.get('cases', [])) if c['id'] == args.case_id]
    if len(selected) != 1 or len(selected[0]['steps']) != 3 or len(selected[0]['expected_results']) != 3:
        parser.error('Select one three-step text-entry/clear case.')
    if selected[0].get('test_data', {}).get('text') != args.value:
        parser.error('Test value must match the selected case data.')
    out.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'run_id': 'browser-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
              'requested_url': args.url, 'case_id': args.case_id,
              'case_file': str(args.case_file.resolve()), 'case_pack_sha256': hashlib.sha256(raw).hexdigest(),
              'started_at': datetime.now(timezone.utc).isoformat(), 'synthetic': False,
              'provenance': 'agent_browser_capture', 'test_executed_by_agent': False,
              'external_issue_created': False, 'form_submitted': False}
    from playwright.sync_api import sync_playwright
    from agent.tools.browser_inputs import check_text_entry, inspect_input_fields
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = context.new_page()
            page.set_default_timeout(12000)
            response = page.goto(args.url, wait_until='domcontentloaded', timeout=25000)
            if urlparse(page.url).hostname != requested.hostname:
                raise ValueError('Navigation left the selected test host; no field interaction performed.')
            page.locator('input').first.wait_for(state='attached', timeout=12000)
            record.update(final_url=page.url, http_status=response.status if response else None,
                          browser='Chromium ' + browser.version, environment='Isolated headless desktop, viewport 1280x900',
                          discovered_fields=inspect_input_fields(page))
            if args.dismiss_button:
                dismiss = page.get_by_role('button', name=args.dismiss_button, exact=True)
                if dismiss.count() != 1 or not dismiss.is_visible():
                    raise ValueError('Selected overlay control is missing or ambiguous; inspect before retrying.')
                dismiss.click()
                record['overlay_action'] = {'role': 'button', 'name': args.dismiss_button, 'clicked': True}
            def capture(stage):
                page.screenshot(path=str(out / (stage + '.png')), full_page=False)
            record['test_executed_by_agent'] = True
            record['result'] = check_text_entry(page, by=args.by, target=args.field, value=args.value, capture=capture)
            record['status'] = record['result']['status']
            record['step_results'] = [{'step_number': i, 'expected_result': selected[0]['expected_results'][i-1],
                'actual': observation, 'status': 'passed' if record['result']['checks'][key] else 'failed',
                'screenshot': str(out / (stage + '.png'))}
                for i, (observation, key, stage) in enumerate(zip(record['result']['observations'],
                    ('initial_empty','exact_value_retained','select_all_backspace_cleared'),('initial','entered','cleared')), 1)]
            context.close(); browser.close()
    except Exception as error:
        record.update(status='incomplete', error_type=type(error).__name__, error=str(error)[:2000])
    record['finished_at'] = datetime.now(timezone.utc).isoformat()
    record['case_pack_unchanged'] = args.case_file.read_bytes() == raw
    record['limitations'] = ['One configured text-input case in Chromium; not all controls, browsers or websites.',
                            'No LLM selected or executed the browser actions in this evaluation.',
                            'The saved-report tool does not authenticate browser captures; raw capture is separate evidence.']
    (out / 'live-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:record.get(k) for k in ('status','case_id','browser','test_executed_by_agent','case_pack_unchanged','error')},ensure_ascii=True))
    return 0 if record['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
