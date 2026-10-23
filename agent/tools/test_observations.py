"""Read saved manual observations and draft defects; never execute or file them."""
import hashlib
import json
import re
from datetime import datetime

MAX_PACK_BYTES = 1_000_000
MAX_REPORT_BYTES = 64_000
MAX_EVIDENCE_BYTES = 1_000_000
MAX_OUTPUT_CHARS = 7_500


class ObservationValidationError(ValueError):
    """Validator-authored feedback, without untrusted source content."""


def _text(value, label, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ObservationValidationError(label + ' must be bounded nonempty text.')
    return value


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - (set(required) | set(optional)) or set(required) - set(value):
        raise ObservationValidationError('Observation data has missing or unregistered fields.')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ObservationValidationError('Duplicate JSON fields are not accepted.')
        result[key] = value
    return result


def _read(path, maximum):
    with path.open('rb') as handle:
        data = handle.read(maximum + 1)
    if len(data) > maximum:
        raise ObservationValidationError('An input file exceeds its reading limit.')
    return data


def _json(raw):
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ObservationValidationError('Input must be unambiguous UTF-8 JSON.') from None


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _identifier(value):
    _text(value, 'Case ID', 64)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
        raise ObservationValidationError('Use a simple case identifier.')
    return value


def draft_test_observations(tools, case_file, observations_file, case_id):
    """Build one evidence-linked draft from files; file metadata never grants approval.

    Supports the WS9 test_cases pack and validate_test_plan cases output. Reports
    bind the exact pack digest. Outcomes are attributed reports, not an agent run
    or an independent verification of the observer, application or evidence.
    """
    _identifier(case_id)
    snapshots = {}

    def snapshot(filename, maximum):
        _text(filename, 'Relative file path', 1500)
        path = tools._resolve_file(filename)
        name = path.relative_to(tools.root).as_posix()
        raw = _read(path, maximum)
        if name in snapshots and snapshots[name][1] != _digest(raw):
            raise ObservationValidationError('An input changed during review; no draft returned.')
        snapshots[name] = (path, _digest(raw), maximum)
        return name, raw

    pack_name, pack_raw = snapshot(case_file, MAX_PACK_BYTES)
    report_name, report_raw = snapshot(observations_file, MAX_REPORT_BYTES)
    pack, report = _json(pack_raw), _json(report_raw)
    if not isinstance(pack, dict) or ('cases' in pack) == ('test_cases' in pack):
        raise ObservationValidationError('Case file needs exactly one cases or test_cases list.')
    cases = pack.get('test_cases', pack.get('cases'))
    if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise ObservationValidationError('Case file needs 1-100 cases.')
    ids, exact_ids, selected = set(), set(), None
    for case in cases:
        if not isinstance(case, dict):
            raise ObservationValidationError('Every case must be an object.')
        identity = _identifier(case.get('id'))
        if identity.casefold() in ids:
            raise ObservationValidationError('Case identifiers must be unique.')
        ids.add(identity.casefold())
        exact_ids.add(identity)
        if identity == case_id:
            selected = case
    if selected is None:
        raise ObservationValidationError('Selected case ID is absent from the case file.')
    _text(selected.get('title'), 'Case title', 200)
    steps, expected = selected.get('steps'), selected.get('expected_results')
    if (not isinstance(steps, list) or not 1 <= len(steps) <= 20
            or not isinstance(expected, list) or len(expected) != len(steps)):
        raise ObservationValidationError('Selected case needs 1-20 paired steps and expected results.')
    for item in steps + expected:
        _text(item, 'Step or expected result')
    if selected.get('questions') or selected.get('unresolved_expectations') :
        raise ObservationValidationError('Resolve selected case questions before comparing results.')

    _fields(report, {'schema_version', 'case_pack_sha256', 'run', 'observations'})
    if type(report['schema_version']) is not int or report['schema_version'] != 1:
        raise ObservationValidationError('Observation schema_version must be 1.')
    if report['case_pack_sha256'] != _digest(pack_raw):
        raise ObservationValidationError('Observation report refers to a different case-pack revision.')
    run = report['run']
    _fields(run, {'id', 'observed_at', 'environment', 'observer', 'provenance'})
    for field in ('id', 'observed_at', 'environment', 'observer'):
        _text(run[field], 'Run ' + field, 300)
    if run['provenance'] not in ('user_report', 'synthetic_fixture'):
        raise ObservationValidationError('Provenance must be user_report or synthetic_fixture; files cannot certify a tool run.')
    try:
        stamp = datetime.fromisoformat(run['observed_at'])
        if stamp.utcoffset() is None:
            raise ValueError()
    except ValueError:
        raise ObservationValidationError('observed_at needs an ISO timestamp with timezone.') from None
    observations = report['observations']
    if not isinstance(observations, list) or len(observations) > 20:
        raise ObservationValidationError('Use at most 20 observations per report.')
    seen, selected_rows = set(), []
    for row in observations:
        _fields(row, {'case_id', 'step_number', 'outcome', 'actual_result', 'evidence'})
        identity = _identifier(row['case_id'])
        number = row['step_number']
        if identity not in exact_ids or type(number) is not int or not 1 <= number <= 20:
            raise ObservationValidationError('Observation needs a known case ID and positive step number.')
        key = (identity.casefold(), number)
        if key in seen:
            raise ObservationValidationError('Duplicate/conflicting observations need a separate run report.')
        seen.add(key)
        if row['outcome'] not in ('passed', 'failed', 'blocked'):
            raise ObservationValidationError('Reported outcomes must be passed, failed or blocked.')
        _text(row['actual_result'], 'Actual result')
        if not isinstance(row['evidence'], list) or not 1 <= len(row['evidence']) <= 3:
            raise ObservationValidationError('Every observed step needs 1-3 evidence references.')
        if identity == case_id:
            if number > len(steps):
                raise ObservationValidationError('Observation step is outside the selected case.')
            selected_rows.append(row)

    records, defects, evidence_files = {}, [], set()
    normalize = lambda value: ' '.join(value.split())
    for row in selected_rows:
        verified = []
        for ref in row['evidence']:
            _fields(ref, {'file', 'start_line', 'end_line', 'quote', 'sha256'})
            start, end = ref['start_line'], ref['end_line']
            if type(start) is not int or type(end) is not int or start < 1 or end < start or end - start >= 80:
                raise ObservationValidationError('Evidence spans need positive line numbers and at most 80 lines.')
            _text(ref['quote'], 'Evidence quote')
            if not isinstance(ref['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', ref['sha256']):
                raise ObservationValidationError('Evidence needs a full lowercase SHA256 digest.')
            name, raw = snapshot(ref['file'], MAX_EVIDENCE_BYTES)
            evidence_files.add(name)
            if len(evidence_files) > 5:
                raise ObservationValidationError('Use at most five evidence files per case.')
            if name in (pack_name, report_name):
                raise ObservationValidationError('Evidence must be separate from the case pack and observation manifest.')
            if _digest(raw) != ref['sha256']:
                raise ObservationValidationError('Evidence revision changed; inspect it before drafting.')
            try:
                lines = raw.decode('utf-8-sig').splitlines()
            except UnicodeDecodeError:
                raise ObservationValidationError('Evidence must be UTF-8 text; image inspection is a separate workflow.') from None
            if end > len(lines) or normalize(ref['quote']) not in normalize('\n'.join(lines[start - 1:end])):
                raise ObservationValidationError('Evidence quote is absent from its cited span.')
            verified.append({**ref, 'file': name})
        if not any(normalize(row['actual_result']) in normalize(ref['quote']) for ref in verified):
            raise ObservationValidationError('Actual-result text must appear in at least one cited evidence quote.')
        number = row['step_number']
        records[number] = {'step_number': number, 'reported_outcome': row['outcome'],
                           'actual_result': row['actual_result'], 'evidence': verified}
        if row['outcome'] == 'failed':
            identity = _digest((run['id'] + '\n' + case_id + '\n' + str(number)).encode())[:16]
            defects.append({'id': 'DRAFT-' + identity, 'status': 'draft_needs_review',
                            'case_id': case_id, 'step_number': number,
                            'title': ('[SYNTHETIC] ' if run['provenance'] == 'synthetic_fixture' else '') + 'Reported failure: ' + selected['title'],
                            'preconditions': selected.get('preconditions', []), 'test_data': selected.get('test_data'),
                            'reproduction_steps': steps[:number], 'expected_result': expected[number - 1],
                            'actual_result': row['actual_result'], 'evidence': verified,
                            'classification': 'unclassified: application/test/data/environment cause not verified',
                            'severity': 'undecided', 'reproduced_by_agent': False,
                            'external_issue_created': False})
    outcomes = [row['outcome'] for row in selected_rows]
    status = ('not_run' if not outcomes else 'reported_failure' if 'failed' in outcomes
              else 'reported_blocked' if 'blocked' in outcomes else 'reported_pass'
              if len(records) == len(steps) else 'partially_observed')
    result = {
        'status': 'P', 'checks': {'input_structure': 'Y', 'case_revision': 'Y', 'cited_text_matches': 'Y',
                                'independent_observation_verification': 'P', 'defect_review': 'P'},
        'case_file': pack_name, 'case_pack_sha256': _digest(pack_raw),
        'observations_file': report_name, 'observations_sha256': _digest(report_raw), 'run': dict(run),
        'case': {'id': case_id, 'title': selected['title'],
                 'status': ('synthetic_' + status if run['provenance'] == 'synthetic_fixture' and status != 'not_run' else status),
                 'requirement_refs': selected.get('source_refs', []),
                 'requirement_verification': 'Copied from the named case pack; underlying requirements not re-read by this tool.',
                 'steps': [{'step_number': i, 'step': step, 'expected_result': expected[i - 1],
                            **records.get(i, {'reported_outcome': 'not_run', 'actual_result': None, 'evidence': []})}
                           for i, step in enumerate(steps, 1)]},
        'defect_drafts': defects, 'synthetic': run['provenance'] == 'synthetic_fixture',
        'test_executed_by_agent': False, 'approval_granted': False, 'external_issue_created': False,
        'limitations': ['Outcomes and observer identity are claims in saved data, not independently verified facts.',
                        'A matching quote/hash verifies the cited saved text, not the application behavior or a defect cause.',
                        'Unobserved steps stay not run. Drafts need review; no test, file write or external filing is performed.']}
    for path, digest, maximum in snapshots.values():
        if _digest(_read(path, maximum)) != digest:
            raise ObservationValidationError('An input changed during review; no draft returned.')
    if len(json.dumps(result, ensure_ascii=False)) > MAX_OUTPUT_CHARS:
        raise ObservationValidationError('Draft exceeds the response limit; use shorter exact notes or a smaller case.')
    return result
