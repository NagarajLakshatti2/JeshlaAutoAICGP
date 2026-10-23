"""Bounded live sample of manual-test planning through the shared agent runtime.

No target writes or execution. Invoke explicitly; excluded from offline discovery.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _declares_not_run(answer):
    """Recognize narrative execution disclaimers, excluding quoted/code evidence."""
    visible=[];fence=None
    for line in answer.splitlines():
        stripped=line.strip()
        if stripped.startswith(('```','~~~')):
            marker=stripped[:3]
            if fence is None:fence=marker
            elif fence==marker:fence=None
            continue
        if fence or stripped.startswith('>'):continue
        visible.append(line)
    text=' '.join(re.sub(r'[*`]', '', '\n'.join(visible)).replace('_',' ').casefold().split())
    patterns=(
        r'\b(?:tests?|test cases?|cases?|examples?)\s+(?:(?:has|have|is|are|was|were)\s+)?not\s+(?:yet\s+)?(?:been\s+)?(?:run|executed)\b',
        r'\bno\s+(?:tests?|test cases?|cases?)\s+(?:were|was|have been|has been)\s+(?:run|executed)\b',
        r'\b(?:test\s+)?execution(?:\s+status)?\s*:\s*(?:not\s+(?:run|executed)|unexecuted)\b',
        r'\b(?:test\s+)?status\s*:\s*not\s+(?:run|executed)\b',
        r'\b(?:tests?|cases?)(?:\s+are)?\s*[:\-]?\s*unexecuted\b')
    return any(re.search(pattern,text) for pattern in patterns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--start-line', type=int, required=True)
    parser.add_argument('--end-line', type=int, required=True)
    parser.add_argument('--provider', choices=['openrouter', 'groq', 'gemini'], default='openrouter')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.start_line <= args.end_line or args.end_line - args.start_line >= 40:
        parser.error('Select a positive source span of at most 40 lines.')
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT / 'outputs' / 'acceptance'):
        parser.error('Evidence must stay under this project outputs/acceptance folder.')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    # These settings affect this explicit evaluation process only.
    os.environ['LLM_ALLOW_LOCAL_OLLAMA'] = 'false'
    os.environ['LLM_FALLBACK_ORDER'] = 'openrouter,groq,gemini'
    os.environ['AI_TECHNICAL_VERIFICATION'] = 'off'
    for prefix in ('OPENROUTER', 'GROQ', 'GEMINI'):
        os.environ[prefix + '_TIMEOUT'] = '20'
        os.environ[prefix + '_CONNECT_ATTEMPTS'] = '1'
    from agent.tools.project_tools import ProjectTools
    from agent.runtime.conversation import answer_question
    from agent.providers.tools import call_tool_messages
    from agent.providers.selection import provider_selection
    from agent.providers.fallback import fallback_scope, last_provider
    from agent.user_errors import user_error_message
    from agent.providers.errors import ProviderError
    output.mkdir(parents=True, exist_ok=True)
    reads, drafts, checked, trace, attempts = [], [], [], [], []
    allowed = {'read_file', 'validate_test_plan'}

    class SampleTools(ProjectTools):
        def read_file(self, relative_path, start_line=1, max_lines=40):
            if relative_path != args.source or start_line != args.start_line or max_lines != args.end_line - args.start_line + 1:
                raise ValueError('Read only the explicitly selected requirement span.')
            reads.append({'file': relative_path, 'start_line': start_line, 'max_lines': max_lines})
            return super().read_file(relative_path, start_line=start_line, max_lines=max_lines)

        def validate_test_plan(self, plan_json=None, plan=None):
            from agent.tools.test_plans import decode_test_plan, TestPlanValidationError
            attempt = {'input': {'plan':plan} if plan is not None else {'plan_json':plan_json}, 'accepted': False}
            attempts.append(attempt)
            try:
                plan = decode_test_plan(plan_json, plan=plan)
                cases=plan.get('cases')
                if not isinstance(cases,list) or len(cases)!=1 or not isinstance(cases[0],dict):
                    raise TestPlanValidationError('This acceptance sample checks exactly one case object.')
                refs=cases[0].get('source_refs')
                if not isinstance(refs,list) or not refs:
                    raise TestPlanValidationError('The sample case requires a source_refs list.')
                for ref in refs:
                    if (not isinstance(ref,dict) or ref.get('file')!=args.source
                            or type(ref.get('start_line')) is not int or type(ref.get('end_line')) is not int
                            or not args.start_line<=ref['start_line']<=ref['end_line']<=args.end_line):
                        raise TestPlanValidationError('Cite only the selected requirement span with integer line numbers.')
                result = super().validate_test_plan(plan=plan)
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                attempt.update(error_type=type(error).__name__, error=str(error)[:300])
                raise
            attempt['accepted'] = True
            drafts.append(plan)
            checked.append(result)
            return result

    tools = SampleTools(args.project_root)
    path = tools._resolve_file(args.source)
    if path.stat().st_size > 1000000:
        parser.error('Requirement source exceeds the bounded fixture size.')
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    def model(messages, specs):
        if len(trace) >= 4:
            raise RuntimeError('Live sample model-call budget reached.')
        offered = [spec for spec in specs if spec['function']['name'] in allowed]
        trace.append({'offered': [spec['function']['name'] for spec in offered]})
        reply = call_tool_messages(messages, offered, max_tokens=2048)
        requested = [call['function']['name'] for call in reply.get('tool_calls', [])]
        trace[-1]['requested'] = requested
        if set(requested) - allowed:
            raise ValueError('Unexpected tool in this confined sample.')
        return reply

    def unavailable(**kwargs):
        raise RuntimeError('No search, indexing, execution or Jira is part of this sample.')

    question = (
        f'Draft exactly one manual test case from {args.source}, lines {args.start_line}-{args.end_line}. '
        f'First read_file with relative_path={args.source!r}, start_line={args.start_line}, '
        f'max_lines={args.end_line - args.start_line + 1}. Use only this requirement, including its supplied data and outcomes. '
        'Then call validate_test_plan using its native plan object with exactly one case and exact source quotes. '
        'Do not add unspecified limits, application details or unrelated tests. '
        'Finally present the checked draft with its case ID, steps, expected results and source reference. '
        'Clearly say human review is pending and tests are not run. No file writes or commands.'
    )
    report = {'status': 'P', 'requested_provider': args.provider, 'question': question,
              'source_sha256_before': before, 'application_tests_executed': False,
              'scope': 'One live-model-generated draft through the shared runtime; no full pilot or release acceptance.'}
    start = time.perf_counter()
    with (output / 'live.log').open('w', encoding='utf-8') as log, redirect_stdout(log), provider_selection(args.provider), fallback_scope() as notices:
        try:
            result = answer_question({'question': question, 'route': 'direct'}, model=model,
                project_root=args.project_root, tools=tools, document_search=unavailable, web=unavailable)
            report['result'] = result
        except Exception as error:
            report['error'] = user_error_message(error)
            report['error_type'] = type(error).__name__
            if isinstance(error,ProviderError):
                report['failed_provider'] = error.provider
                report['failure_category'] = error.category
        report['actual_provider'] = last_provider(args.provider) if any('requested' in row for row in trace) else None
        report['fallback_notices'] = list(notices)
    report.update(seconds=round(time.perf_counter() - start, 2), reads=reads, drafts=drafts,
                  checked_plans=checked, validation_attempts=attempts, model_trace=trace,
                  source_unchanged=hashlib.sha256(path.read_bytes()).hexdigest() == before)
    answer = report.get('result', {}).get('answer', '')
    report['checks'] = {'read_selected_requirement': bool(reads), 'checked_one_draft': len(checked) == 1,
        'completed': report.get('result', {}).get('execution_outcome') == 'completed',
        'source_unchanged': report['source_unchanged'],
        'draft_not_run': bool(checked) and all(c['execution_status'] == 'not_run' and c['actual_result'] is None for p in checked for c in p['cases']),
        'human_review_pending': bool(checked) and all(p['checks']['human_review'] == 'P' and not p['approval_granted'] for p in checked),
        'final_discloses_not_run': _declares_not_run(answer),
        'final_includes_case_id': bool(checked) and checked[0]['cases'][0]['id'] in answer}
    if all(report['checks'].values()):
        report['status'] = 'Y - sampled live planning behavior; human semantic review remains P'
    (output / 'live.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'checks': report['checks'], 'seconds': report['seconds']}))
    return 0 if report['status'].startswith('Y') else 1


if __name__ == '__main__':
    raise SystemExit(main())
