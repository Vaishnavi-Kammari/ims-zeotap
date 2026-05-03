from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import WorkItemOut, WorkItemListResponse, WorkItemStatusUpdate, RCACreate, RCAOut
from app.models.sql_models import WorkItemStatus
from app.services.work_item_service import (
    get_work_items, get_work_item, transition_work_item,
    create_rca, get_signals_for_work_item
)
from app.core.state_machine import InvalidTransitionError, RequiresRCAError

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("", response_model=WorkItemListResponse)
async def list_incidents(
    status: Optional[WorkItemStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """List all incidents sorted by priority then recency."""
    items, total = await get_work_items(status=status, limit=limit, skip=skip)
    return WorkItemListResponse(
        items=[WorkItemOut.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{incident_id}", response_model=WorkItemOut)
async def get_incident(incident_id: UUID):
    """Get a single incident with its RCA (if any)."""
    item = await get_work_item(incident_id)
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")
    return WorkItemOut.model_validate(item)


@router.patch("/{incident_id}/status", response_model=WorkItemOut)
async def update_incident_status(incident_id: UUID, body: WorkItemStatusUpdate):
    """
    Transition an incident through its lifecycle.
    OPEN → INVESTIGATING → RESOLVED → CLOSED
    Closing requires a valid RCA.
    """
    try:
        item = await transition_work_item(incident_id, body.status)
        return WorkItemOut.model_validate(item)
    except RequiresRCAError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{incident_id}/rca", response_model=RCAOut, status_code=status.HTTP_201_CREATED)
async def submit_rca(incident_id: UUID, body: RCACreate):
    """
    Submit Root Cause Analysis for an incident.
    RCA is required before the incident can be CLOSED.
    """
    try:
        rca = await create_rca(incident_id, body)
        return RCAOut.model_validate(rca)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{incident_id}/signals")
async def get_incident_signals(
    incident_id: UUID,
    limit: int = Query(100, ge=1, le=500),
):
    """Get raw signals from MongoDB linked to this incident."""
    signals = await get_signals_for_work_item(str(incident_id), limit=limit)
    return {"signals": signals, "count": len(signals)}
