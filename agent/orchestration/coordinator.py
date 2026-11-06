"""Small, sequential coordinator for explicitly registered specialists.

The coordinator routes a goal; it does not grant tools or approve actions.
Each specialist receives only the tools registered for its capability.
"""
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from agent.orchestration.handoff import Handoff
from agent.orchestration.controls import RunControl


@dataclass(frozen=True)
class Specialist:
    name: str
    run: Callable[[str, Handoff, RunControl], Any]


class Coordinator:
    def __init__(self, specialists: Mapping[str, Specialist]):
        self._specialists = dict(specialists)

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._specialists))

    def select(self, goal: str, requested_capability: str) -> dict:
        """Select a registered specialist for this explicit capability."""
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("A non-empty user goal is required.")
        if not isinstance(requested_capability, str) or not requested_capability.strip():
            raise ValueError("An explicit capability is required.")
        specialist = self._specialists.get(requested_capability)
        if specialist is None:
            return {"status": "unsupported", "capability": requested_capability,
                    "message": f"The {requested_capability} capability is not available."}
        return {"status": "selected", "capability": requested_capability,
                "specialist": specialist}

    def dispatch(self, goal: str, requested_capability: str, handoff: Handoff,
                 control: RunControl, *, depth: int = 0) -> dict:
        """Dispatch the unchanged user goal or report the capability unsupported."""
        if not isinstance(handoff, Handoff):
            raise ValueError("Dispatch requires a host-created trusted handoff.")
        if not isinstance(control, RunControl):
            raise ValueError("Dispatch requires shared host run controls.")
        if not handoff.permits(requested_capability):
            return {"status": "unsupported", "capability": requested_capability,
                    "message": "This capability is outside the handoff scope."}
        selection = self.select(goal, requested_capability)
        if selection["status"] == "unsupported":
            return selection
        try:
            control.check(depth)
            control.charge(delegations=1)
            result = selection["specialist"].run(goal, handoff, control)
            control.check(depth)
        except Exception as error:
            return {"status": "cancelled" if control.cancelled else "incomplete",
                    "capability": requested_capability,
                    "message": str(error) if isinstance(error, RuntimeError)
                    else "Specialist work did not complete; no result was returned."}
        return {"status": "completed", "capability": requested_capability,
                "result": result}


def filesystem_specialist(project_tools, executor: Callable[[str, Mapping[str, Callable]], Any]) -> Specialist:
    """Create a read-only specialist whose executor receives only scoped read tools."""
    if not callable(executor):
        raise ValueError("A host-configured specialist executor is required.")

    def inspect(goal: str, handoff: Handoff, control: RunControl) -> dict:
        # These methods are already confined to ProjectTools.root and enforce
        # excluded paths, supported text types, and bounded reads.
        def guarded(method):
            def call(**arguments):
                control.check(0)
                control.charge(tool_calls=1)
                result = method(**arguments)
                control.check(0)
                return result
            return call

        tools = {"list_files": guarded(project_tools.list_files),
                 "read_file": guarded(project_tools.read_file)}
        return executor(goal, tools)
    return Specialist("File System", inspect)


def api_specialist(project_tools, executor: Callable[[str, Mapping[str, Callable]], Any]) -> Specialist:
    """Create a read-only API source specialist; it cannot run requests or tests."""
    if not callable(executor):
        raise ValueError("A host-configured API specialist executor is required.")

    def inspect(goal: str, handoff: Handoff, control: RunControl) -> Any:
        def guarded(method):
            def call(**arguments):
                control.check(0)
                control.charge(tool_calls=1)
                result = method(**arguments)
                control.check(0)
                return result
            return call
        tools = {"list_files": guarded(project_tools.list_files),
                 "read_file": guarded(project_tools.read_file),
                 "search_text": guarded(project_tools.search_text)}
        return executor(goal, tools)
    return Specialist("API", inspect)


def project_coordinator(project_tools, *, filesystem_executor, api_executor=None) -> Coordinator:
    """Build the supported registry for one selected project and host executors."""
    specialists = {"File System": filesystem_specialist(project_tools, filesystem_executor)}
    if api_executor is not None:
        specialists["API"] = api_specialist(project_tools, api_executor)
    return Coordinator(specialists)
