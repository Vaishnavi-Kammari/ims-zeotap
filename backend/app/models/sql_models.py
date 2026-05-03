import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, DateTime, Float, Text, ForeignKey,
    Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Priority(str, PyEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class WorkItemStatus(str, PyEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ComponentType(str, PyEnum):
    RDBMS = "RDBMS"
    NOSQL = "NOSQL"
    CACHE = "CACHE"
    API = "API"
    QUEUE = "QUEUE"
    MCP_HOST = "MCP_HOST"


class RootCauseCategory(str, PyEnum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    APPLICATION = "APPLICATION"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    HUMAN_ERROR = "HUMAN_ERROR"
    THIRD_PARTY = "THIRD_PARTY"
    UNKNOWN = "UNKNOWN"


class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_id = Column(String(255), nullable=False, index=True)
    component_type = Column(Enum(ComponentType), nullable=False)
    priority = Column(Enum(Priority), nullable=False)
    status = Column(Enum(WorkItemStatus), nullable=False, default=WorkItemStatus.OPEN)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    signal_count = Column(String(20), nullable=False, default="1")
    start_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    mttr_minutes = Column(Float, nullable=True)

    rca = relationship("RCARecord", back_populates="work_item", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_work_items_status_priority", "status", "priority"),
    )


class RCARecord(Base):
    __tablename__ = "rca_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_item_id = Column(UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    incident_start = Column(DateTime(timezone=True), nullable=False)
    incident_end = Column(DateTime(timezone=True), nullable=False)
    root_cause_category = Column(Enum(RootCauseCategory), nullable=False)
    fix_applied = Column(Text, nullable=False)
    prevention_steps = Column(Text, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    submitted_by = Column(String(255), nullable=True, default="system")

    work_item = relationship("WorkItem", back_populates="rca")

    __table_args__ = (
        UniqueConstraint("work_item_id", name="uq_rca_work_item"),
    )
