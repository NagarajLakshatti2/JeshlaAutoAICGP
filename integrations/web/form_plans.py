"""Bind a login draft to saved form observations and local requirements only."""
import hashlib
import json
import re

from agent.tools.test_plans import decode_test_plan, validate_test_plan
from agent.tools.web_pages import url_location
from integrations.web.inspection import validate_public_browser_address


def _observed(items, index, label):
    if type(index) is not int or index < 1:
        raise ValueError('Use a positive observed ' + label + ' index.')
    matches = [item for item in items if isinstance(item, dict) and item.get('index') == index]
    if len(matches) != 1:
        raise ValueError('The observed ' + label + ' is missing or ambiguous.')
    return matches[0]


def validate_login_plan(tools, plan):
    """No model, navigation, source edits, submission or execution approval."""
    plan = decode_test_plan(plan=plan)
    required = {'inspection_file', 'inspection_sha256', 'url', 'pinned_address',
                'form_index', 'username_index', 'password_index', 'submit_index', 'cases'}
    if set(plan) != required:
        raise ValueError('Login plan has missing or unregistered fields.')
    digest = plan['inspection_sha256']
    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
        raise ValueError('Use the full saved inspection hash.')
    path = tools._resolve_file(plan['inspection_file'])
    with path.open('rb') as handle:
        raw = handle.read(65001)
    if len(raw) > 65000 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Inspection changed; inspect and review again.')
    snapshot = json.loads(raw)
    if not isinstance(snapshot, dict) or snapshot.get('status') != 'inspected':
        raise ValueError('A completed inspection is required.')
    if snapshot.get('url') != plan['url'] or url_location(plan['url'])[0].scheme != 'https':
        raise ValueError('Use the exact inspected HTTPS page.')
    validate_public_browser_address(plan['pinned_address'])
    if snapshot.get('pinned_address') != plan['pinned_address']:
        raise ValueError('Use the address bound to this inspection.')
    for key in ('fields', 'buttons', 'forms'):
        if not isinstance(snapshot.get(key), list) or snapshot.get(key + '_may_be_truncated') is not False:
            raise ValueError('Login binding requires complete form-control observations; inspect again.')
    form = _observed(snapshot['forms'], plan['form_index'], 'form')
    username = _observed(snapshot['fields'], plan['username_index'], 'username')
    password = _observed(snapshot['fields'], plan['password_index'], 'password')
    submit = _observed(snapshot['buttons'], plan['submit_index'], 'submit button')
    if not form.get('id') or form.get('id_unique') is not True:
        raise ValueError('This pilot requires an inspected unique form ID.')
    for field, types in ((username, {'text', 'email'}), (password, {'password'})):
        if (field.get('tag') != 'input' or field.get('type') not in types
                or field.get('disabled') is not False or field.get('read_only') is not False
                or field.get('aria_disabled') is not False
                or not field.get('id') or field.get('id_unique') is not True):
            raise ValueError('Use observed editable fields with unique IDs and correct login types.')
    if (username is password or any(type(item.get('form_index')) is not int
            or item['form_index'] != form['index'] for item in (username, password, submit))):
        raise ValueError('Username, password and submit must belong to the same inspected form.')
    if (submit.get('tag') != 'button' or submit.get('type') != 'submit'
            or submit.get('in_form') is not True or submit.get('disabled') is not False
            or submit.get('aria_disabled') is not False or not submit.get('name')
            or submit.get('name_in_form_unique') is not True):
        raise ValueError('Use an enabled, uniquely named submit button in the inspected form.')
    cases = plan['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 3:
        raise ValueError('Select one to three bounded login cases.')
    prepared = []
    for case in cases:
        keys = {'id', 'title', 'source_refs', 'steps', 'expected_results', 'credentials', 'outcome'}
        if not isinstance(case, dict) or set(case) != keys:
            raise ValueError('Login case has missing or unregistered fields.')
        credentials = case['credentials']
        if (not isinstance(credentials, dict) or set(credentials) != {'username', 'password'}
                or any(not isinstance(v, str) or len(v) > 150 for v in credentials.values())):
            raise ValueError('Use bounded source-backed login data.')
        if not isinstance(case['outcome'], str) or case['outcome'] not in {'success', 'error', 'required'}:
            raise ValueError('Use a declared success, error or required-field outcome.')
        if case['outcome'] == 'required':
            if any(credentials.values()):
                raise ValueError('Required-field cases must leave both login fields empty.')
        elif not all(v.strip() for v in credentials.values()):
            raise ValueError('Success/error cases require both source-backed values.')
        refs = case['source_refs']
        if not isinstance(refs, list) or not all(isinstance(ref, dict) for ref in refs):
            raise ValueError('Use local requirement references.')
        for value in credentials.values():
            if value and not any(isinstance(ref.get('quote'), str) and value in ref['quote'] for ref in refs):
                raise ValueError('Login data must occur in the cited requirement; do not invent credentials.')
        prepared.append({key: case[key] for key in ('id', 'title', 'source_refs', 'steps', 'expected_results')})
    checked = validate_test_plan(tools, plan={'cases': prepared})
    # Reject concurrent replacement of the inspection after source checking.
    with path.open('rb') as handle:
        if hashlib.sha256(handle.read(65001)).hexdigest() != digest:
            raise ValueError('Inspection changed during validation; review again.')
    return {'status': 'P', 'checks': {'structure': 'Y', 'inspection_binding': 'Y',
            'source_traceability': checked['checks']['source_traceability'],
            'human_review': 'P', 'execution': 'P'},
            'controls': {'form': form, 'username': username, 'password': password, 'submit': submit},
            'cases': checked['cases'], 'sources': checked['sources'],
            'execution_status': 'not_run', 'approval_granted': False,
            'limitations': checked['limitations'] + [
                'Observed form ownership and source membership are checked, not application behavior.',
                'Outcome assertions, fresh page bindings and separate source/run approvals remain required.',
                'No password value was read from a browser. Credential mappings are omitted; cited requirement quotes remain visible.']}
