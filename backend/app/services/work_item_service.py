"""
Work Item and RCA service.

Handles:
- Listing and retrieving work items (with Redis cache)
- State transitions via StateMachine
- RCA creation and MTTR calculation
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.db.postgres import AsyncSessionLocal
from app.db.redis_client import cache_set, cache_get, cache_delete, DASHBOARD_KEY
from app.models.sql_models import WorkItem, RCARecord, WorkItemStatus
from app.models.schemas import RCACreate, WorkItemOut
from app.core.state_machine import WorkItemStateMachine, InvalidTransitionError, RequiresRCAError

logger = logging.getLogger(__name__)

CACHE_TTL = 30  # seconds


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def get_work_items(
    status: Optional[WorkItemStatus] = None,
    limit: int = 50,
    skip: int = 0,
) -> tuple[list[WorkItem], int]:
    """Fetch work items, using Redis cache for dashboard queries."""

    # Only cache uncfiltered dashboard calls
    use_cache = status is None and skip == 0 and limit <= 50
    if use_cache:
        cached = await cache_get(DASHBOARD_KEY)
        if cached:
            items = [WorkItem(**_reconstruct(i)) for i in cached["items"]]
            return items, cached["total"]

    async with AsyncSessionLocal() as session:
        q = select(WorkItem).options(selectinload(WorkItem.rca))
        if status:
            q = q.where(WorkItem.status == status)
        q = q.order_by(WorkItem.priority, desc(WorkItem.start_time)).limit(limit).offset(skip)

        result = await session.execute(q)
        items = result.scalars().all()

        count_q = select(WorkItem)
        if status:
            count_q = count_q.where(WorkItem.status == status)
        count_result = await session.execute(count_q)
        total = len(count_result.scalars().all())

        if use_cache:
            serializable = [WorkItemOut.model_validate(i).model_dump(mode="json") for i in items]
            await cache_set(DASHBOARD_KEY, {"items": serializable, "total": total}, CACHE_TTL)

        return list(items), total


def _reconstruct(data: dict) -> dict:
    """Reconstruct WorkItem from cached dict (simplified)."""
    return data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def get_work_item(work_item_id: UUID) -> Optional[WorkItem]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkItem)
            .options(selectinload(WorkItem.rca))
            .where(WorkItem.id == work_item_id)
        )
        return result.scalar_one_or_none()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def transition_work_item(
    work_item_id: UUID,
    target_status: WorkItemStatus,
) -> WorkItem:
    """
    Validate and apply a state transition using WorkItemStateMachine.
    Raises InvalidTransitionError or RequiresRCAError on invalid moves.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkItem)
            .options(selectinload(WorkItem.rca))
            .where(WorkItem.id == work_item_id)
            .with_for_update()  # row-level lock for concurrency safety
        )
        work_item = result.scalar_one_or_none()

        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        machine = WorkItemStateMachine(
            current_status=work_item.status,
            has_rca=work_item.rca is not None,
        )
        machine.transition(target_status)  # raises on invalid

        work_item.status = target_status
        if target_status == WorkItemStatus.CLOSED:
            work_item.closed_at = datetime.now(timezone.utc)
            # Calculate MTTR
            if work_item.rca:
                delta = work_item.rca.incident_end - work_item.start_time
                work_item.mttr_minutes = round(delta.total_seconds() / 60, 2)

        await session.commit()
        await session.refresh(work_item)
        await cache_delete(DASHBOARD_KEY)
        logger.info(f"Work Item {work_item_id} → {target_status.value}")
        return work_item


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def create_rca(work_item_id: UUID, rca_data: RCACreate) -> RCARecord:
    """
    Create an RCA record for a work item.
    Validates RCA completeness before saving.
    """
    async with AsyncSessionLocal() as session:
        # Check work item exists
        wi_result = await session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = wi_result.scalar_one_or_none()
        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        if work_item.status == WorkItemStatus.CLOSED:
            raise InvalidTransitionError("Cannot modify RCA on a closed work item")

        # Check no existing RCA
        existing = await session.execute(
            select(RCARecord).where(RCARecord.work_item_id == work_item_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("RCA already exists for this work item. Update instead.")

        rca = RCARecord(
            work_item_id=work_item_id,
            incident_start=rca_data.incident_start,
            incident_end=rca_data.incident_end,
            root_cause_category=rca_data.root_cause_category,
            fix_applied=rca_data.fix_applied,
            prevention_steps=rca_data.prevention_steps,
            submitted_by=rca_data.submitted_by,
        )
        session.add(rca)
        await session.commit()
        await session.refresh(rca)
        await cache_delete(DASHBOARD_KEY)
        logger.info(f"RCA created for Work Item {work_item_id}")
        return rca


async def get_signals_for_work_item(work_item_id: str, limit: int = 100) -> list[dict]:
    """Fetch raw signals from MongoDB for a work item."""
    from app.db.mongo import get_mongo_db
    db = get_mongo_db()
    cursor = db.signals.find(
        {"work_item_id": work_item_id},
        {"_id": 0},
    ).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)
