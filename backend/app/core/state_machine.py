"""
State Pattern implementation for Work Item lifecycle.

OPEN → INVESTIGATING → RESOLVED → CLOSED

Rules:
- Can only move forward (no rollback)
- CLOSED requires a valid RCA record
"""
from app.models.sql_models import WorkItemStatus


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""
    pass


class RequiresRCAError(Exception):
    """Raised when closing without a complete RCA."""
    pass


# Valid transitions: current_status → {allowed_next_statuses}
_TRANSITIONS: dict[WorkItemStatus, set[WorkItemStatus]] = {
    WorkItemStatus.OPEN: {WorkItemStatus.INVESTIGATING},
    WorkItemStatus.INVESTIGATING: {WorkItemStatus.RESOLVED},
    WorkItemStatus.RESOLVED: {WorkItemStatus.CLOSED},
    WorkItemStatus.CLOSED: set(),  # terminal state
}


class WorkItemStateMachine:
    """
    Encapsulates all transition logic for a Work Item.
    Validates rules before mutating the entity.
    """

    def __init__(self, current_status: WorkItemStatus, has_rca: bool = False):
        self.current_status = current_status
        self.has_rca = has_rca

    def can_transition_to(self, target: WorkItemStatus) -> bool:
        return target in _TRANSITIONS.get(self.current_status, set())

    def transition(self, target: WorkItemStatus) -> WorkItemStatus:
        """
        Validates and performs state transition.
        Returns the new status.
        Raises InvalidTransitionError or RequiresRCAError on invalid move.
        """
        if not self.can_transition_to(target):
            allowed = [s.value for s in _TRANSITIONS.get(self.current_status, set())]
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_status.value} to {target.value}. "
                f"Allowed: {allowed or ['none (terminal state)']}"
            )

        if target == WorkItemStatus.CLOSED and not self.has_rca:
            raise RequiresRCAError(
                "Cannot close a Work Item without a complete RCA record. "
                "Please submit the Root Cause Analysis first."
            )

        self.current_status = target
        return self.current_status

    @staticmethod
    def allowed_transitions(status: WorkItemStatus) -> list[str]:
        return [s.value for s in _TRANSITIONS.get(status, set())]
