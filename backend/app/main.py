"""
Incident Management System — FastAPI Application

Architecture:
  - Async-first (asyncio throughout)
  - Bounded in-memory queue for backpressure
  - Worker pool for parallel signal processing
  - Rate limiting on ingestion endpoints
  - WebSocket for live UI feed
"""
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.db.postgres import init_db
from app.db.mongo import init_mongo, close_mongo
from app.db.redis_client import init_redis, close_redis, get_redis
from app.workers.signal_queue import signal_processor_worker, metrics_reporter, signal_queue
from app.services.signal_service import process_signal
from app.api import signals, incidents, health, websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Mission-Critical Incident Management System",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(signals.router)
app.include_router(incidents.router)
app.include_router(websocket.router)

# ── Background tasks ──────────────────────────────────────────────────────────
_background_tasks: list[asyncio.Task] = []


@app.on_event("startup")
async def startup():
    logger.info("Starting IMS backend...")

    # Init storage
    await init_db()
    logger.info("PostgreSQL initialized")

    await init_mongo()
    logger.info("MongoDB initialized")

    await init_redis()
    logger.info("Redis initialized")

    # Start worker pool
    for i in range(settings.WORKER_CONCURRENCY):
        task = asyncio.create_task(
            signal_processor_worker(i, process_signal),
            name=f"signal-worker-{i}",
        )
        _background_tasks.append(task)
    logger.info(f"Started {settings.WORKER_CONCURRENCY} signal workers")

    # Start metrics reporter
    metrics_task = asyncio.create_task(metrics_reporter(), name="metrics-reporter")
    _background_tasks.append(metrics_task)

    logger.info("IMS backend started ✓")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down IMS backend...")

    for task in _background_tasks:
        task.cancel()

    await asyncio.gather(*_background_tasks, return_exceptions=True)

    # Drain remaining queue items
    remaining = signal_queue.qsize()
    if remaining:
        logger.warning(f"Shutdown with {remaining} unprocessed signals in queue")

    await close_mongo()
    await close_redis()
    logger.info("IMS backend stopped")
