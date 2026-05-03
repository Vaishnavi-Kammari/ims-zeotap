"""
Strategy Pattern implementation for incident alerting.

Different component failures map to different alert strategies:
- P0: RDBMS, MCP_HOST  → Critical (page on-call immediately)
- P1: API, QUEUE       → High (alert team channel)
- P2: CACHE, NOSQL     → Medium (create ticket, notify async)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.sql_models import ComponentType, Priority


@dataclass
class AlertPayload:
    work_item_id: str
    component_id: str
    component_type: ComponentType
    priority: Priority
    title: str
    signal_count: int
    timestamp: datetime


class AlertStrategy(ABC):
    """Base alerting strategy."""

    @property
    @abstractmethod
    def priority(self) -> Priority:
        ...

    @abstractmethod
    async def send_alert(self, payload: AlertPayload) -> dict:
        ...


class P0CriticalAlertStrategy(AlertStrategy):
    """
    P0: System-wide outage. Immediately pages on-call.
    Components: RDBMS, MCP_HOST
    """

    @property
    def priority(self) -> Priority:
        return Priority.P0

    async def send_alert(self, payload: AlertPayload) -> dict:
        alert = {
            "level": "CRITICAL",
            "priority": "P0",
            "action": "PAGE_ON_CALL",
            "channel": "#incidents-critical",
            "work_item_id": str(payload.work_item_id),
            "component": payload.component_id,
            "title": f"[P0 CRITICAL] {payload.title}",
            "message": (
                f"CRITICAL OUTAGE: {payload.component_id} ({payload.component_type.value}) "
                f"has generated {payload.signal_count} error signals. "
                f"Work Item: {payload.work_item_id}. Immediate response required."
            ),
            "timestamp": payload.timestamp.isoformat(),
        }
        # In production: call PagerDuty / OpsGenie / SMS gateway
        print(f"🚨 [ALERT P0] {alert['message']}")
        return alert


class P1HighAlertStrategy(AlertStrategy):
    """
    P1: Service degradation. Alert team Slack channel.
    Components: API, QUEUE
    """

    @property
    def priority(self) -> Priority:
        return Priority.P1

    async def send_alert(self, payload: AlertPayload) -> dict:
        alert = {
            "level": "HIGH",
            "priority": "P1",
            "action": "NOTIFY_TEAM",
            "channel": "#incidents-high",
            "work_item_id": str(payload.work_item_id),
            "component": payload.component_id,
            "title": f"[P1 HIGH] {payload.title}",
            "message": (
                f"HIGH SEVERITY: {payload.component_id} ({payload.component_type.value}) "
                f"experiencing issues. {payload.signal_count} signals received. "
                f"Work Item: {payload.work_item_id}. Investigate promptly."
            ),
            "timestamp": payload.timestamp.isoformat(),
        }
        print(f"⚠️  [ALERT P1] {alert['message']}")
        return alert


class P2MediumAlertStrategy(AlertStrategy):
    """
    P2: Partial degradation. Create ticket and notify async.
    Components: CACHE, NOSQL
    """

    @property
    def priority(self) -> Priority:
        return Priority.P2

    async def send_alert(self, payload: AlertPayload) -> dict:
        alert = {
            "level": "MEDIUM",
            "priority": "P2",
            "action": "CREATE_TICKET",
            "channel": "#incidents-medium",
            "work_item_id": str(payload.work_item_id),
            "component": payload.component_id,
            "title": f"[P2 MEDIUM] {payload.title}",
            "message": (
                f"MEDIUM: {payload.component_id} ({payload.component_type.value}) "
                f"showing degraded performance. {payload.signal_count} signals. "
                f"Work Item: {payload.work_item_id}. Review during business hours."
            ),
            "timestamp": payload.timestamp.isoformat(),
        }
        print(f"📋 [ALERT P2] {alert['message']}")
        return alert


# ── Priority routing ─────────────────────────────────────────────────────────

_COMPONENT_PRIORITY_MAP: dict[ComponentType, Priority] = {
    ComponentType.RDBMS: Priority.P0,
    ComponentType.MCP_HOST: Priority.P0,
    ComponentType.API: Priority.P1,
    ComponentType.QUEUE: Priority.P1,
    ComponentType.CACHE: Priority.P2,
    ComponentType.NOSQL: Priority.P2,
}

_STRATEGY_MAP: dict[Priority, AlertStrategy] = {
    Priority.P0: P0CriticalAlertStrategy(),
    Priority.P1: P1HighAlertStrategy(),
    Priority.P2: P2MediumAlertStrategy(),
}


def get_priority_for_component(component_type: ComponentType) -> Priority:
    return _COMPONENT_PRIORITY_MAP.get(component_type, Priority.P1)


def get_alert_strategy(priority: Priority) -> AlertStrategy:
    return _STRATEGY_MAP[priority]
