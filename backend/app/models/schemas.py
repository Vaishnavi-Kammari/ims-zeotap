from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.sql_models import (
    Priority, WorkItemStatus, ComponentType, RootCauseCategory
)


# ── Signal schemas ──────────────────────────────────────────────────────────

class SignalPayload(BaseModel):
    component_id: str = Field(..., min_length=1, max_length=255)
    component_type: ComponentType
    error_code: str = Field(..., max_length=100)
    message: str = Field(..., max_length=2000)
    latency_ms: Optional[float] = None
    metadata: Optional[dict] = None
    timestamp: Optional[datetime] = None


class SignalResponse(BaseModel):
    signal_id: str
    work_item_id: Optional[str] = None
    debounced: bool = False
    message: str


# ── RCA schemas ─────────────────────────────────────────────────────────────

class RCACreate(BaseModel):
    incident_start: datetime
    incident_end: datetime
    root_cause_category: RootCauseCategory
    fix_applied: str = Field(..., min_length=10)
    prevention_steps: str = Field(..., min_length=10)
    submitted_by: Optional[str] = "anonymous"

    @model_validator(mode="after")
    def validate_times(self) -> RCACreate:
        if self.incident_end <= self.incident_start:
            raise ValueError("incident_end must be after incident_start")
        return self


class RCAOut(BaseModel):
    id: UUID
    work_item_id: UUID
    incident_start: datetime
    incident_end: datetime
    root_cause_category: RootCauseCategory
    fix_applied: str
    prevention_steps: str
    submitted_at: datetime
    submitted_by: Optional[str]

    model_config = {"from_attributes": True}


# ── Work item schemas ───────────────────────────────────────────────────────

class WorkItemOut(BaseModel):
    id: UUID
    component_id: str
    component_type: ComponentType
    priority: Priority
    status: WorkItemStatus
    title: str
    description: Optional[str]
    signal_count: str
    start_time: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    mttr_minutes: Optional[float]
    rca: Optional[RCAOut] = None

    model_config = {"from_attributes": True}


class WorkItemStatusUpdate(BaseModel):
    status: WorkItemStatus


class WorkItemListResponse(BaseModel):
    items: List[WorkItemOut]
    total: int


# ── Signal detail (from MongoDB) ────────────────────────────────────────────

class SignalDetail(BaseModel):
    signal_id: str
    work_item_id: str
    component_id: str
    component_type: str
    error_code: str
    message: str
    latency_ms: Optional[float]
    metadata: Optional[dict]
    timestamp: datetime
