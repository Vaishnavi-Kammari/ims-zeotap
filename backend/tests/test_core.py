"""
Unit tests for:
- RCA validation logic
- Work Item state machine transitions
- Alert strategy routing
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.core.state_machine import (
    WorkItemStateMachine,
    InvalidTransitionError,
    RequiresRCAError,
)
from app.core.alert_strategies import (
    get_priority_for_component,
    get_alert_strategy,
    AlertPayload,
)
from app.models.sql_models import (
    WorkItemStatus, ComponentType, Priority
)
from app.models.schemas import RCACreate


# ── State Machine Tests ──────────────────────────────────────────────────────

class TestWorkItemStateMachine:

    def test_open_can_move_to_investigating(self):
        machine = WorkItemStateMachine(WorkItemStatus.OPEN)
        result = machine.transition(WorkItemStatus.INVESTIGATING)
        assert result == WorkItemStatus.INVESTIGATING

    def test_investigating_can_move_to_resolved(self):
        machine = WorkItemStateMachine(WorkItemStatus.INVESTIGATING)
        result = machine.transition(WorkItemStatus.RESOLVED)
        assert result == WorkItemStatus.RESOLVED

    def test_resolved_can_move_to_closed_with_rca(self):
        machine = WorkItemStateMachine(WorkItemStatus.RESOLVED, has_rca=True)
        result = machine.transition(WorkItemStatus.CLOSED)
        assert result == WorkItemStatus.CLOSED

    def test_cannot_skip_states(self):
        machine = WorkItemStateMachine(WorkItemStatus.OPEN)
        with pytest.raises(InvalidTransitionError):
            machine.transition(WorkItemStatus.RESOLVED)

    def test_cannot_go_backwards(self):
        machine = WorkItemStateMachine(WorkItemStatus.INVESTIGATING)
        with pytest.raises(InvalidTransitionError):
            machine.transition(WorkItemStatus.OPEN)

    def test_cannot_close_without_rca(self):
        machine = WorkItemStateMachine(WorkItemStatus.RESOLVED, has_rca=False)
        with pytest.raises(RequiresRCAError):
            machine.transition(WorkItemStatus.CLOSED)

    def test_closed_is_terminal(self):
        machine = WorkItemStateMachine(WorkItemStatus.CLOSED, has_rca=True)
        with pytest.raises(InvalidTransitionError):
            machine.transition(WorkItemStatus.OPEN)

    def test_allowed_transitions_from_open(self):
        allowed = WorkItemStateMachine.allowed_transitions(WorkItemStatus.OPEN)
        assert "INVESTIGATING" in allowed

    def test_allowed_transitions_from_closed_is_empty(self):
        allowed = WorkItemStateMachine.allowed_transitions(WorkItemStatus.CLOSED)
        assert allowed == []


# ── RCA Validation Tests ─────────────────────────────────────────────────────

class TestRCAValidation:

    def _make_rca(self, **overrides):
        defaults = {
            "incident_start": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            "incident_end": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            "root_cause_category": "INFRASTRUCTURE",
            "fix_applied": "Restarted the database service and cleared stale locks",
            "prevention_steps": "Added automated restart policy and disk space monitoring alerts",
        }
        defaults.update(overrides)
        return RCACreate(**defaults)

    def test_valid_rca_passes(self):
        rca = self._make_rca()
        assert rca.fix_applied is not None
        assert rca.prevention_steps is not None

    def test_end_before_start_fails(self):
        with pytest.raises(ValueError, match="incident_end must be after"):
            self._make_rca(
                incident_start=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                incident_end=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            )

    def test_end_equal_start_fails(self):
        t = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            self._make_rca(incident_start=t, incident_end=t)

    def test_fix_applied_too_short_fails(self):
        with pytest.raises(ValueError):
            self._make_rca(fix_applied="short")

    def test_prevention_steps_too_short_fails(self):
        with pytest.raises(ValueError):
            self._make_rca(prevention_steps="short")


# ── Alert Strategy Tests ─────────────────────────────────────────────────────

class TestAlertStrategies:

    def test_rdbms_maps_to_p0(self):
        priority = get_priority_for_component(ComponentType.RDBMS)
        assert priority == Priority.P0

    def test_mcp_host_maps_to_p0(self):
        priority = get_priority_for_component(ComponentType.MCP_HOST)
        assert priority == Priority.P0

    def test_api_maps_to_p1(self):
        priority = get_priority_for_component(ComponentType.API)
        assert priority == Priority.P1

    def test_queue_maps_to_p1(self):
        priority = get_priority_for_component(ComponentType.QUEUE)
        assert priority == Priority.P1

    def test_cache_maps_to_p2(self):
        priority = get_priority_for_component(ComponentType.CACHE)
        assert priority == Priority.P2

    def test_nosql_maps_to_p2(self):
        priority = get_priority_for_component(ComponentType.NOSQL)
        assert priority == Priority.P2

    @pytest.mark.asyncio
    async def test_p0_strategy_sends_alert(self):
        strategy = get_alert_strategy(Priority.P0)
        payload = AlertPayload(
            work_item_id="test-id",
            component_id="DB_01",
            component_type=ComponentType.RDBMS,
            priority=Priority.P0,
            title="DB down",
            signal_count=5,
            timestamp=datetime.now(timezone.utc),
        )
        result = await strategy.send_alert(payload)
        assert result["priority"] == "P0"
        assert result["action"] == "PAGE_ON_CALL"

    @pytest.mark.asyncio
    async def test_p2_strategy_creates_ticket(self):
        strategy = get_alert_strategy(Priority.P2)
        payload = AlertPayload(
            work_item_id="test-id-2",
            component_id="CACHE_01",
            component_type=ComponentType.CACHE,
            priority=Priority.P2,
            title="Cache miss spike",
            signal_count=10,
            timestamp=datetime.now(timezone.utc),
        )
        result = await strategy.send_alert(payload)
        assert result["priority"] == "P2"
        assert result["action"] == "CREATE_TICKET"
