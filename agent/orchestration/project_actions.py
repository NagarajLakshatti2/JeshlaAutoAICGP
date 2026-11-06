"""Specialists propose one project action. The host owns validation and execution."""
from dataclasses import dataclass
from uuid import uuid4

from agent.orchestration.controls import RunControl
from agent.orchestration.coordinator import Coordinator, Specialist
from agent.orchestration.handoff import Handoff


@dataclass(frozen=True)
class ProjectAction:
    capability: str
    name: str
    goal: str


ROLES = {"inspect_browser_page": "Browser", "discover_jira_traceability": "Jira"}


def route_project_action(state, action, control, task_id):
    role = ROLES[action]
    scope = {key: state[key] for key in
             ("memory_user_id", "memory_namespace", "project_id", "bound_project_root")}
    if state.get("jira_scope"):
        scope["jira_scope"] = state["jira_scope"]
    handoff = Handoff.from_request_scope(
        request_scope=scope, chat_id=state["conversation_session"], task_id=task_id,
        allowed_capabilities=(role,), remaining_budget=dict(control.remaining))

    def propose(goal, handoff, shared):
        shared.charge(tool_calls=1)
        return ProjectAction(role, action, goal)

    outcome = Coordinator({role: Specialist(role, propose)}).dispatch(
        state["question"], role, handoff, control)
    if outcome["status"] != "completed":
        raise ValueError(outcome["message"])
    return outcome["result"]


def project_action_turn(max_steps):
    return RunControl({"delegations": max_steps, "tool_calls": max_steps}, max_depth=1), uuid4().hex
