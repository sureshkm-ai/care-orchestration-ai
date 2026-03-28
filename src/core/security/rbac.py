"""Role-Based Access Control for healthcare agents.

Each agent has a role that maps to permitted scopes.
Scopes follow the pattern: {resource}:{action} (BD-5).
"""

from __future__ import annotations

from enum import Enum

from src.core.errors import AuthorizationError


class AgentRole(str, Enum):
    TRIAGE = "triage"
    CARE_COORDINATOR = "care_coordinator"
    CLINICAL_DATA = "clinical_data"
    PHARMACY = "pharmacy"
    ORCHESTRATOR = "orchestrator"


# Role -> permitted scopes
ROLE_PERMISSIONS: dict[AgentRole, set[str]] = {
    AgentRole.TRIAGE: {
        "patient:read",
        "observation:read",
        "condition:read",
        "intake:write",
        "triage:write",
        "triage:read",
    },
    AgentRole.CARE_COORDINATOR: {
        "patient:read",
        "appointment:read",
        "appointment:write",
        "triage:read",
        "care_plan:write",
        "care_plan:read",
    },
    AgentRole.CLINICAL_DATA: {
        "patient:read",
        "observation:read",
        "observation:write",
        "condition:read",
        "condition:write",
        "medication:read",
        "encounter:read",
        "encounter:write",
    },
    AgentRole.PHARMACY: {
        "patient:read",
        "medication:read",
        "medication:write",
        "interaction:read",
        "prescription:write",
        "prescription:read",
    },
    AgentRole.ORCHESTRATOR: {
        "patient:read",
        "triage:read",
        "appointment:read",
        "care_plan:read",
    },
}


def has_permission(role: AgentRole, scope: str) -> bool:
    """Check if a role has a specific permission scope."""
    return scope in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: AgentRole, scope: str) -> None:
    """Require that a role has a scope. Raises AuthorizationError if not."""
    if not has_permission(role, scope):
        raise AuthorizationError(f"Role '{role.value}' does not have permission: {scope}")


def get_role_scopes(role: AgentRole) -> list[str]:
    """Get all scopes for a role."""
    return sorted(ROLE_PERMISSIONS.get(role, set()))
