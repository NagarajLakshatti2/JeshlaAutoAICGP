"""Validated trusted context passed between coordinator and specialists."""
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Handoff:
    owner_id: str
    project_id: str
    chat_id: str
    task_id: str
    allowed_capabilities: tuple[str, ...]
    remaining_budget: dict
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_request_scope(cls, *, request_scope, chat_id, task_id,
                           allowed_capabilities, remaining_budget,
                           evidence_refs=()):
        """Build identity only from the application's validated request scope."""
        from agent.runtime.project_scope import validate_request_scope
        scope = validate_request_scope(request_scope)
        required = ("memory_user_id", "project_id", "bound_project_root")
        if any(not scope.get(key) for key in required):
            raise ValueError("A selected project and owner are required for specialist handoff.")
        return cls.create(
            owner_id=scope["memory_user_id"], project_id=scope["project_id"],
            chat_id=chat_id, task_id=task_id,
            allowed_capabilities=allowed_capabilities,
            remaining_budget=remaining_budget, evidence_refs=evidence_refs)

    @classmethod
    def create(cls, *, owner_id, project_id, chat_id, task_id,
               allowed_capabilities: Iterable[str], remaining_budget: dict,
               evidence_refs: Iterable[str] = ()):
        """Create only from host-validated request identity and budget values."""
        identities = (owner_id, project_id, chat_id, task_id)
        if any(not isinstance(value, str) or not value.strip() or len(value) > 256
               for value in identities):
            raise ValueError("Handoff identities must be non-empty bounded strings.")
        capabilities = tuple(allowed_capabilities)
        if not capabilities or any(not isinstance(item, str) or not item.strip()
                                   for item in capabilities):
            raise ValueError("Handoff requires explicit allowed capabilities.")
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("Handoff capabilities must be unique.")
        if not isinstance(remaining_budget, dict) or not remaining_budget:
            raise ValueError("Handoff requires a remaining budget.")
        budget = dict(remaining_budget)
        if any(not isinstance(key, str) or not key.strip() or type(value) not in (int, float)
               or value < 0 for key, value in budget.items()):
            raise ValueError("Handoff budget values must be non-negative numbers.")
        refs = tuple(evidence_refs)
        if any(not isinstance(ref, str) or not ref.strip() or len(ref) > 512 for ref in refs):
            raise ValueError("Evidence references must be bounded non-empty strings.")
        return cls(*identities, capabilities, budget, refs)

    def permits(self, capability: str) -> bool:
        return capability in self.allowed_capabilities
