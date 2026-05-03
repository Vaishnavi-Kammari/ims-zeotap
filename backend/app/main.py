import asyncio
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.db.postgres import init_db
from app.db.mongo import init_mongo, close_mongo
from app.db.redis_client import init_redis, close_redis
from app.workers.signal_queue import (
    signal_processor_worker, metrics_reporter, signal_queue
)
from app.services.signal_service import process_signal
from app.api import signals, incidents, health, websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(signals.router)
app.include_router(incidents.router)
app.include_router(websocket.router)

_background_tasks: list[asyncio.Task] = []


@app.on_event("startup")
async def startup():
    logger.info("Starting IMS backend...")

    # Give databases extra time to be ready on Windows
    time.sleep(5)

    try:
        await init_db()
        logger.info("✓ PostgreSQL ready")
    except Exception as e:
        logger.error(f"✗ PostgreSQL error: {e}")

    try:
        await init_mongo()
        logger.info("✓ MongoDB ready")
    except Exception as e:
        logger.error(f"✗ MongoDB error: {e}")

    try:
        await init_redis()
        logger.info("✓ Redis ready")
    except Exception as e:
        logger.error(f"✗ Redis error: {e}")

    for i in range(settings.WORKER_CONCURRENCY):
        task = asyncio.create_task(
            signal_processor_worker(i, process_signal),
            name=f"worker-{i}",
        )
        _background_tasks.append(task)

    task = asyncio.create_task(metrics_reporter(), name="metrics")
    _background_tasks.append(task)

    logger.info("✓ IMS backend started successfully")


@app.on_event("shutdown")
async def shutdown():
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    await close_mongo()
    await close_redis()
    logger.info("IMS stopped")
