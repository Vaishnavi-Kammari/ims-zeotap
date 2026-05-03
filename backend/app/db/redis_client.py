import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None

DASHBOARD_KEY = "ims:dashboard:incidents"
METRICS_KEY = "ims:metrics:throughput"
DEBOUNCE_PREFIX = "ims:debounce:"
SIGNAL_COUNTER_KEY = "ims:metrics:signal_count"


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def init_redis() -> None:
    r = get_redis()
    await r.ping()


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Dashboard cache helpers ─────────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


# ── Debounce helpers ────────────────────────────────────────────────────────

async def debounce_check_and_increment(component_id: str, window: int) -> int:
    """Atomically increment signal count for component within time window.
    Returns current count after increment."""
    r = get_redis()
    key = f"{DEBOUNCE_PREFIX}{component_id}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = await pipe.execute()
    return results[0]


async def debounce_get_work_item(component_id: str) -> Optional[str]:
    r = get_redis()
    return await r.get(f"{DEBOUNCE_PREFIX}wi:{component_id}")


async def debounce_set_work_item(component_id: str, work_item_id: str, window: int) -> None:
    r = get_redis()
    await r.setex(f"{DEBOUNCE_PREFIX}wi:{component_id}", window * 6, work_item_id)


# ── Metrics helpers ─────────────────────────────────────────────────────────

async def increment_signal_counter() -> None:
    r = get_redis()
    await r.incr(SIGNAL_COUNTER_KEY)


async def get_and_reset_signal_counter() -> int:
    r = get_redis()
    val = await r.getdel(SIGNAL_COUNTER_KEY)
    return int(val) if val else 0
