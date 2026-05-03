from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.models.schemas import SignalPayload, SignalResponse
from app.workers.signal_queue import enqueue_signal

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.post("", response_model=SignalResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(payload: SignalPayload, request: Request):
    """
    Ingest a signal from a monitored component.

    Accepts up to 10,000 signals/sec via bounded in-memory queue.
    Returns 202 Accepted immediately — processing is async.
    Returns 429 if queue is saturated (backpressure).
    """
    signal_dict = payload.model_dump()
    if signal_dict.get("timestamp") is None:
        signal_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    else:
        signal_dict["timestamp"] = signal_dict["timestamp"].isoformat()

    queued = await enqueue_signal(signal_dict)

    if not queued:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Signal queue is at capacity. Apply backpressure at source.",
        )

    return SignalResponse(
        signal_id="pending",
        message="Signal accepted for async processing",
    )


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_batch(payloads: list[SignalPayload]):
    """Batch ingestion endpoint — up to 500 signals per request."""
    if len(payloads) > 500:
        raise HTTPException(status_code=400, detail="Max 500 signals per batch request")

    accepted = 0
    dropped = 0
    for payload in payloads:
        signal_dict = payload.model_dump()
        if signal_dict.get("timestamp") is None:
            signal_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        else:
            signal_dict["timestamp"] = signal_dict["timestamp"].isoformat()

        queued = await enqueue_signal(signal_dict)
        if queued:
            accepted += 1
        else:
            dropped += 1

    return {"accepted": accepted, "dropped": dropped}
