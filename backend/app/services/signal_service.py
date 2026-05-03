"""
Core signal processing service.

Handles:
- Debouncing (100 signals/10s per component_id → 1 work item)
- Work item creation in PostgreSQL
- Raw signal storage in MongoDB
- Cache invalidation in Redis
- Alert dispatch
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from sqlalchemy import select, update

from app.db.postgres import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.db.redis_client import (
    debounce_check_and_increment,
    debounce_get_work_item,
    debounce_set_work_item,
    cache_delete,
    DASHBOARD_KEY,
)
from app.models.sql_models import WorkItem, WorkItemStatus, ComponentType
from app.core.alert_strategies import (
    get_priority_for_component,
    get_alert_strategy,
    AlertPayload,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _persist_work_item(work_item: WorkItem) -> WorkItem:
    """Persist work item to PostgreSQL with retry logic."""
    async with AsyncSessionLocal() as session:
        session.add(work_item)
        await session.commit()
        await session.refresh(work_item)
        return work_item


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _increment_work_item_signal_count(work_item_id: str) -> None:
    """Atomically increment signal count on an existing work item."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(WorkItem)
            .where(WorkItem.id == work_item_id)
            .values(signal_count=WorkItem.signal_count + 1)
        )
        await session.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _persist_signal_to_mongo(signal_doc: dict) -> None:
    """Persist raw signal to MongoDB with retry logic."""
    db = get_mongo_db()
    await db.signals.insert_one(signal_doc)


async def process_signal(signal: dict) -> dict:
    """
    Main signal processing pipeline:
    1. Check debounce window
    2. Route to existing or new work item
    3. Persist signal to MongoDB
    4. Send alert if new work item
    5. Invalidate dashboard cache
    """
    component_id: str = signal["component_id"]
    component_type_str: str = signal["component_type"]
    component_type = ComponentType(component_type_str)
    now = datetime.now(timezone.utc)

    signal_id = str(uuid4())
    signal["signal_id"] = signal_id
    signal["received_at"] = now.isoformat()

    # ── Step 1: Debounce check ────────────────────────────────────────────
    count = await debounce_check_and_increment(component_id, settings.DEBOUNCE_WINDOW_SECONDS)
    existing_wi_id = await debounce_get_work_item(component_id)

    if existing_wi_id:
        # Debounced: link signal to existing work item
        signal["work_item_id"] = existing_wi_id
        await _persist_signal_to_mongo({**signal, "debounced": True})
        await _increment_work_item_signal_count(existing_wi_id)
        logger.debug(f"Signal debounced → WI {existing_wi_id} (count={count})")
        return {"signal_id": signal_id, "work_item_id": existing_wi_id, "debounced": True}

    # ── Step 2: Create new Work Item ──────────────────────────────────────
    priority = get_priority_for_component(component_type)
    work_item = WorkItem(
        component_id=component_id,
        component_type=component_type,
        priority=priority,
        status=WorkItemStatus.OPEN,
        title=f"{component_type.value} failure: {component_id}",
        description=f"Error {signal.get('error_code', 'UNKNOWN')}: {signal.get('message', '')}",
        signal_count="1",
        start_time=now,
    )

    saved_wi = await _persist_work_item(work_item)
    wi_id = str(saved_wi.id)

    # Register in debounce cache
    await debounce_set_work_item(component_id, wi_id, settings.DEBOUNCE_WINDOW_SECONDS)

    # ── Step 3: Persist raw signal to MongoDB ─────────────────────────────
    signal["work_item_id"] = wi_id
    signal["debounced"] = False
    await _persist_signal_to_mongo(signal)

    # ── Step 4: Send alert ────────────────────────────────────────────────
    strategy = get_alert_strategy(priority)
    alert_payload = AlertPayload(
        work_item_id=wi_id,
        component_id=component_id,
        component_type=component_type,
        priority=priority,
        title=work_item.title,
        signal_count=1,
        timestamp=now,
    )
    await strategy.send_alert(alert_payload)

    # ── Step 5: Invalidate dashboard cache ────────────────────────────────
    await cache_delete(DASHBOARD_KEY)

    logger.info(f"New Work Item created: {wi_id} for {component_id} [{priority.value}]")
    return {"signal_id": signal_id, "work_item_id": wi_id, "debounced": False}
