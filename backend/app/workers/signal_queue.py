"""
Async signal queue with backpressure and worker pool.

- asyncio.Queue with bounded maxsize prevents memory exhaustion
- Worker pool drains the queue concurrently
- Metrics are tracked and printed every N seconds
"""
import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings
from app.db.redis_client import increment_signal_counter, get_and_reset_signal_counter

logger = logging.getLogger(__name__)
settings = get_settings()

# Global bounded queue — the backpressure mechanism
signal_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.SIGNAL_QUEUE_MAXSIZE)

# Tracks dropped signals due to full queue
_dropped_count: int = 0
_processed_count: int = 0


async def enqueue_signal(signal: dict) -> bool:
    """
    Non-blocking enqueue. Returns True if queued, False if dropped.
    Uses put_nowait to avoid blocking the ingestion endpoint.
    """
    global _dropped_count
    try:
        signal_queue.put_nowait(signal)
        await increment_signal_counter()
        return True
    except asyncio.QueueFull:
        _dropped_count += 1
        logger.warning(
            f"Queue full ({signal_queue.maxsize} items). "
            f"Dropping signal for {signal.get('component_id', 'unknown')}. "
            f"Total dropped: {_dropped_count}"
        )
        return False


async def signal_processor_worker(worker_id: int, process_fn) -> None:
    """Individual worker that dequeues and processes signals."""
    global _processed_count
    logger.info(f"Worker {worker_id} started")

    while True:
        try:
            signal = await asyncio.wait_for(signal_queue.get(), timeout=1.0)
            try:
                await process_fn(signal)
                _processed_count += 1
            except Exception as e:
                logger.error(f"Worker {worker_id} failed to process signal: {e}")
            finally:
                signal_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} shutting down")
            break


async def metrics_reporter() -> None:
    """Periodically prints throughput metrics to console."""
    interval = settings.METRICS_INTERVAL_SECONDS
    logger.info(f"Metrics reporter started (interval: {interval}s)")

    while True:
        try:
            await asyncio.sleep(interval)
            count = await get_and_reset_signal_counter()
            rate = count / interval
            queue_size = signal_queue.qsize()
            print(
                f"\n📊 [METRICS] "
                f"Throughput: {rate:.1f} signals/sec | "
                f"Queue depth: {queue_size} | "
                f"Total processed: {_processed_count} | "
                f"Dropped: {_dropped_count} | "
                f"Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Metrics reporter error: {e}")
