import time
from fastapi import APIRouter
from app.db.postgres import engine
from app.db.mongo import get_mongo_db
from app.db.redis_client import get_redis
from app.workers.signal_queue import signal_queue, _processed_count, _dropped_count

router = APIRouter(tags=["observability"])

_start_time = time.time()


@router.get("/health")
async def health_check():
    """Health check endpoint. Verifies all storage backends."""
    checks = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)[:100]}"

    # MongoDB
    try:
        db = get_mongo_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {str(e)[:100]}"

    # Redis
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"

    # Queue
    checks["queue"] = {
        "depth": signal_queue.qsize(),
        "maxsize": signal_queue.maxsize,
        "utilization_pct": round(signal_queue.qsize() / signal_queue.maxsize * 100, 1),
    }

    all_ok = all(v == "ok" for k, v in checks.items() if k != "queue")
    uptime_seconds = round(time.time() - _start_time, 1)

    return {
        "status": "healthy" if all_ok else "degraded",
        "uptime_seconds": uptime_seconds,
        "checks": checks,
        "metrics": {
            "signals_processed": _processed_count,
            "signals_dropped": _dropped_count,
        },
    }


@router.get("/metrics")
async def get_metrics():
    """Expose throughput and queue metrics."""
    return {
        "queue_depth": signal_queue.qsize(),
        "queue_capacity": signal_queue.maxsize,
        "signals_processed_total": _processed_count,
        "signals_dropped_total": _dropped_count,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }
