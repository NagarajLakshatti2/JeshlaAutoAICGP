"""Bind reviewed text-test inputs to actual inspection and requirement artifacts."""
import hashlib
import json
from agent.tools.test_plans import validate_test_plan


def validate_web_plan(tools,plan):
    if not isinstance(plan,dict):raise ValueError('Web plan must be an object.')
    path=tools._resolve_file(plan.get('inspection_file',''))
    raw=path.read_bytes()
    if len(raw)>65000 or hashlib.sha256(raw).hexdigest()!=plan.get('inspection_sha256'):
        raise ValueError('Inspected page artifact changed; inspect/review again.')
    inspection=json.loads(raw)
    if inspection.get('status')!='inspected' or inspection.get('url')!=plan.get('url'):
        raise ValueError('Run URL must match the inspected page.')
    if inspection.get('pinned_address')!=plan.get('pinned_address'):
        raise ValueError('Use the public address bound to this inspection.')
    number=plan.get('field_index')
    if type(number) is not int:raise ValueError('Use an observed field index.')
    fields=inspection.get('fields',[])
    matches=[field for field in fields if field.get('index')==number]
    if len(matches)!=1:raise ValueError('Field index is missing or ambiguous.')
    field=matches[0];key={'label':'label','placeholder':'placeholder'}.get(plan.get('locator_by'))
    if (not key or not plan.get('locator_text') or field.get(key)!=plan['locator_text']
            or sum(f.get(key)==plan['locator_text'] for f in fields)!=1):
        raise ValueError('Use an exact unique inspected label or placeholder.')
    if field.get('tag')!='input' or field.get('type')!='text' or field.get('disabled') or field.get('read_only'):
        raise ValueError('This pilot supports only an inspected editable ordinary text input.')
    dismiss=plan.get('dismiss_button','')
    if dismiss and (dismiss!='Decline' or not any(b.get('name')==dismiss and b.get('in_form') is False
            and b.get('disabled') is False for b in inspection.get('buttons',[]))):
        raise ValueError('Cookie action must match an inspected non-form refusal button.')
    value=plan.get('test_value');reference=plan.get('source_ref')
    if not isinstance(value,str) or not value or len(value)>500 or not isinstance(reference,dict):
        raise ValueError('Source-backed bounded test data and a source reference are required.')
    if value not in reference.get('quote',''):
        raise ValueError('Selected text value must be present in the cited requirement.')
    checked=validate_test_plan(tools,plan={'cases':[{'id':plan.get('case_id'),
        'title':'Reviewed text entry and clearing','source_refs':[reference],
        'steps':['Enter the selected requirement value.','Clear the same field.'],
        'expected_results':['The full value equals the selected test data.','The field value is empty after clearing.']}]})
    return {'structure':'Y','inspection_binding':'Y','source_traceability':checked['checks']['source_traceability'],
            'note':'Source membership and inspected-element binding only; user scope/review supplies the entry/clear intent. This does not grant execution approval.'}
