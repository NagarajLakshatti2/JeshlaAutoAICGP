"""Host entry point for one scoped, read-only specialist dispatch."""
from uuid import uuid4
import hashlib
import json

from agent.orchestration.controls import RunControl
from agent.orchestration.coordinator import project_coordinator
from agent.orchestration.handoff import Handoff
from agent.runtime.project_scope import validate_request_scope
from agent.tools.project_tools import ProjectTools


def dispatch_project_capability(*, capability, request_scope, chat_id, goal, executor,
                                budget=None, task_id=None, evidence_refs=(),
                                control=None):
    """Run one registered read-only specialist under validated project scope.

    ``executor`` is host-owned and receives only this project's bounded
    read-only project functions. Specialist text cannot alter
    identity, capabilities, budget, evidence references, or approval state.
    """
    validated = validate_request_scope(request_scope)
    if not validated or not validated.get("project_id"):
        raise ValueError("Select a saved project before dispatching a specialist.")
    effective_budget = {"delegations": 1, "tool_calls": 10, "time_seconds": 30} if budget is None else dict(budget)
    if not {"delegations", "tool_calls", "time_seconds"}.issubset(effective_budget):
        raise ValueError("Budget must include delegation, tool-call and time limits.")
    current_task_id = task_id or uuid4().hex
    handoff = Handoff.from_request_scope(
        request_scope=request_scope, chat_id=chat_id, task_id=current_task_id,
        allowed_capabilities=(capability,),
        remaining_budget=effective_budget, evidence_refs=evidence_refs)
    shared_control = control or RunControl(dict(handoff.remaining_budget))
    if shared_control.remaining != handoff.remaining_budget:
        raise ValueError("Handoff and shared run budgets must match.")
    tools = ProjectTools(validated["bound_project_root"], project_id=validated["project_id"])
    evidence_refs = []

    def recording_executor(original_goal, scoped_tools):
        def record(name, **arguments):
            data = scoped_tools[name](**arguments)
            serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            evidence_refs.append(f"{current_task_id}:{len(evidence_refs) + 1}:{name}:{digest}")
            return data
        return executor(original_goal, {name: (lambda _record=record, _name=name, **args: _record(_name, **args))
                                        for name in scoped_tools})

    coordinator = project_coordinator(
        tools,
        filesystem_executor=recording_executor if capability == "File System" else lambda *_: None,
        api_executor=recording_executor if capability == "API" else None)
    outcome = coordinator.dispatch(goal, capability, handoff, shared_control)
    outcome["evidence_refs"] = tuple(evidence_refs)
    return outcome


def dispatch_project_filesystem(**kwargs):
    return dispatch_project_capability(capability="File System", **kwargs)


def dispatch_project_api(**kwargs):
    return dispatch_project_capability(capability="API", **kwargs)
