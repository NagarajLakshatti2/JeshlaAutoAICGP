"""Validate a manual-test draft against local source spans; never approve or run it."""
import hashlib
import json
import re

MAX_PLAN_CHARS = 12000
MAX_CASES = 20
MAX_SOURCES = 5
MAX_SOURCE_BYTES = 1000000


class TestPlanValidationError(ValueError):
    """A bounded validator-authored message safe for draft-format feedback."""


def _text(value, label, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TestPlanValidationError(label + ' must be bounded nonempty text.')
    return value


def _text_list(value, label, *, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= 20:
        raise TestPlanValidationError(label + ' must be a bounded list of text.')
    for item in value:
        _text(item, label)
    return value


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise TestPlanValidationError('Duplicate JSON fields are not accepted.')
        value[key] = item
    return value


def _read_source(path):
    with path.open('rb') as handle:
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise TestPlanValidationError('A requirement source exceeds the reading limit.')
    return raw


def decode_test_plan(plan_json=None, *, plan=None):
    """Normalize exactly one bounded native object or legacy JSON-string input."""
    if (plan_json is None) == (plan is None):
        raise TestPlanValidationError('Supply exactly one plan object or legacy plan_json string.')
    if plan is not None:
        if not isinstance(plan, dict):
            raise TestPlanValidationError('plan must be a JSON object.')
        try:
            plan_json = json.dumps(plan, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError):
            raise TestPlanValidationError('plan must contain bounded JSON data only.') from None
    _text(plan_json, 'plan input', MAX_PLAN_CHARS)
    try:
        decoded = json.loads(plan_json, object_pairs_hook=_unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (TypeError, ValueError, RecursionError):
        raise TestPlanValidationError('plan input must be unambiguous valid JSON.') from None
    if not isinstance(decoded, dict):
        raise TestPlanValidationError('plan input must be a JSON object.')
    return decoded


def test_plan_schema():
    """Native nested schema; canonical validation still enforces all boundaries."""
    def text(limit=500):return {'type':'string','minLength':1,'maxLength':limit}
    def array(item,minimum=0,maximum=20):return {'type':'array','items':item,'minItems':minimum,'maxItems':maximum}
    ref={'type':'object','properties':{'file':text(1500),'start_line':{'type':'integer','minimum':1},
         'end_line':{'type':'integer','minimum':1},'quote':text(), 'sha256':{'type':'string','minLength':64,'maxLength':64}},
         'required':['file','start_line','end_line','quote'],'additionalProperties':False}
    case={'type':'object','properties':{'id':text(64),'title':text(200),'source_refs':array(ref,1,5),
          'steps':array(text(),1),'expected_results':array(text()),'questions':array(text()),'test_data':text(2000)},
          'required':['id','title','source_refs','steps','expected_results'],'additionalProperties':False}
    return {'type':'object','properties':{'cases':array(case,1,MAX_CASES),'clarifications':array(text())},
            'required':['cases'],'additionalProperties':False}


def validate_test_plan(tools, plan_json=None, *, plan=None):
    """Return Y/P checks and not-run cases; source membership is not entailment."""
    plan = decode_test_plan(plan_json, plan=plan)
    if not isinstance(plan, dict) or set(plan) - {'cases', 'clarifications'}:
        raise TestPlanValidationError('A plan accepts only cases and optional clarifications.')
    cases = plan.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise TestPlanValidationError('A plan must contain 1-20 cases; narrow a larger draft.')
    clarifications = _text_list(plan.get('clarifications', []), 'clarifications')
    identities = set()
    prepared = []
    paths = {}
    for index, case in enumerate(cases):
        label = 'cases[' + str(index) + ']'
        required = {'id', 'title', 'source_refs', 'steps', 'expected_results'}
        allowed = required | {'questions', 'test_data'}
        if not isinstance(case, dict) or set(case) - allowed or required - set(case):
            raise TestPlanValidationError(label + ' has missing or unregistered fields.')
        identity = _text(case['id'], label + '.id', 64)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', identity):
            raise TestPlanValidationError(label + '.id must be a simple case identifier.')
        if identity.casefold() in identities:
            raise TestPlanValidationError('Case identifiers must be unique.')
        identities.add(identity.casefold())
        _text(case['title'], label + '.title', 200)
        _text_list(case['steps'], label + '.steps', minimum=1)
        expected = _text_list(case['expected_results'], label + '.expected_results')
        questions = _text_list(case.get('questions', []), label + '.questions')
        if not expected and not questions:
            raise TestPlanValidationError(label + ' needs expected results or an explicit unresolved question.')
        if 'test_data' in case:
            _text(case['test_data'], label + '.test_data', 2000)
        refs = case['source_refs']
        if not isinstance(refs, list) or not 1 <= len(refs) <= 5:
            raise TestPlanValidationError(label + '.source_refs must contain 1-5 local source spans.')
        prepared_refs = []
        for reference in refs:
            fields = {'file', 'start_line', 'end_line', 'quote'}
            if not isinstance(reference, dict) or fields - set(reference) or set(reference) - (fields | {'sha256'}):
                raise TestPlanValidationError(label + '.source_refs has missing or unregistered fields.')
            filename = _text(reference['file'], label + '.source_refs.file', 1500)
            _text(reference['quote'], label + '.source_refs.quote')
            start, end = reference['start_line'], reference['end_line']
            if type(start) is not int or type(end) is not int or start < 1 or end < start or end - start >= 80:
                raise TestPlanValidationError('Source spans need positive line numbers and at most 80 lines.')
            if 'sha256' in reference and (not isinstance(reference['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', reference['sha256'])):
                raise TestPlanValidationError('A supplied source SHA256 must be a lowercase full digest.')
            path = tools._resolve_file(filename)
            canonical = path.relative_to(tools.root).as_posix()
            paths[canonical] = path
            if len(paths) > MAX_SOURCES:
                raise TestPlanValidationError('Use at most five source files per test-plan check.')
            prepared_refs.append((canonical, reference))
        prepared.append((case, questions, prepared_refs))
    snapshots = {}
    for name, path in paths.items():
        raw = _read_source(path)
        try:
            lines = raw.decode('utf-8-sig').splitlines()
        except UnicodeDecodeError:
            raise TestPlanValidationError('Requirement sources must be UTF-8 text.') from None
        snapshots[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'lines': lines}
    result_cases = []
    normalize = lambda value: ' '.join(value.split())
    for case, questions, references in prepared:
        verified = []
        for name, reference in references:
            snapshot = snapshots[name]
            if reference.get('sha256', snapshot['sha256']) != snapshot['sha256']:
                raise TestPlanValidationError('A source revision changed; read it again before checking the plan.')
            if reference['end_line'] > len(snapshot['lines']):
                raise TestPlanValidationError('A cited source span is outside the actual file.')
            excerpt = '\n'.join(snapshot['lines'][reference['start_line'] - 1:reference['end_line']])
            if normalize(reference['quote']) not in normalize(excerpt):
                raise TestPlanValidationError('A source quote is absent from the cited file span.')
            verified.append({**reference, 'file': name, 'sha256': snapshot['sha256']})
        result_cases.append({**case, 'source_refs': verified, 'questions': list(questions),
                             'review_status': 'P', 'execution_status': 'not_run', 'actual_result': None})
    for name, path in paths.items():
        if hashlib.sha256(_read_source(path)).hexdigest() != snapshots[name]['sha256']:
            raise TestPlanValidationError('A source changed during review; no checked plan was returned.')
    return {
        'status': 'P',
        'checks': {'structure': 'Y', 'source_traceability': 'Y',
                   'clarifications': 'P' if clarifications or any(c['questions'] for c in result_cases) else 'Y',
                   'human_review': 'P', 'factual_correctness': 'P', 'execution': 'P'},
        'cases': result_cases, 'clarifications': list(clarifications),
        'sources': [{'file': name, 'sha256': value['sha256'], 'total_lines': len(value['lines'])} for name, value in snapshots.items()],
        'execution_status': 'not_run', 'approval_granted': False,
        'limitations': ['Quotes match the named file spans at this check; this does not prove that each expectation follows from the requirement.',
                        'The draft needs human review. No code, test, file write, Jira action or approval was executed.']}
