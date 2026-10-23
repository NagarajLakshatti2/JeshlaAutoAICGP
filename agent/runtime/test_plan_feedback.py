"""One trusted draft correction; unrelated or truncated results never clear it."""
import json
import re


def _scope(cases):
    if not isinstance(cases, list) or not 1 <= len(cases) <= 20:
        return None
    rows=[]
    for case in cases:
        if not isinstance(case,dict):return None
        identity=case.get('id');refs=case.get('source_refs')
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',identity):return None
        if not isinstance(refs,list) or not 1<=len(refs)<=5:return None
        files=[]
        for ref in refs:
            if not isinstance(ref,dict) or not isinstance(ref.get('file'),str) or not ref['file'].strip() or len(ref['file'])>1500:return None
            files.append(ref['file'])
        rows.append((identity,tuple(sorted(set(files)))))
    if len({identity.casefold() for identity,_ in rows})!=len(rows):return None
    return tuple(sorted(rows))


def _object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate field')
        result[key]=value
    return result


class PlanCorrection:
    def __init__(self):
        self.pending=False
        self.expected_scope=None
        self.corrections_used=0

    def begin_check(self):
        if self.pending:
            if self.corrections_used>=1:return False
            self.corrections_used+=1
        return True

    def reject(self, plan_json, error):
        if not self.pending:
            try:
                plan=plan_json if isinstance(plan_json,dict) else json.loads(plan_json,object_pairs_hook=_object)
                self.expected_scope=_scope(plan.get('cases')) if isinstance(plan,dict) else None
            except (ValueError,TypeError,RecursionError):self.expected_scope=None
        self.pending=True
        return {'error':'Test-plan draft rejected.','validation_error':str(error)[:300],
                'correction_allowed':self.corrections_used<1,
                'instruction':'Correct only the reported draft data, preserving case IDs and source files. Use the registered schema and exact source quotes; do not add approvals or actual results.',
                'status':'P','execution_status':'not_run','approval_granted':False}

    def observe_visible(self, data):
        if not self.pending or self.expected_scope is None:return
        try:result=json.loads(data)
        except (ValueError,TypeError):return
        if not isinstance(result,dict) or result.get('error') or result.get('status')!='P':return
        checks=result.get('checks',{})
        if not isinstance(checks,dict) or any(checks.get(k)!='Y' for k in ('structure','source_traceability')):return
        if any(checks.get(k)!='P' for k in ('human_review','factual_correctness','execution')):return
        if result.get('approval_granted') is not False or result.get('execution_status')!='not_run':return
        cases=result.get('cases')
        if _scope(cases)!=self.expected_scope:return
        if any(c.get('execution_status')!='not_run' or c.get('actual_result') is not None for c in cases):return
        self.pending=False

    @staticmethod
    def incomplete(tool_succeeded):
        return {'answer':'The requested test-plan draft has not passed bounded validation. No complete checked plan is claimed; review the reported requirement or schema issue.',
                'task_status':'incomplete','answer_available':False,
                'execution_outcome':'partial' if tool_succeeded else 'blocked'}
