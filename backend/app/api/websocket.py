"""
WebSocket endpoint for live incident feed.

Clients connect and receive real-time updates when incidents change.
Uses a simple pub/sub pattern with a set of active connections.
"""
import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Active WebSocket connections
_connections: Set[WebSocket] = set()


async def broadcast(event_type: str, data: dict) -> None:
    """Broadcast a message to all connected WebSocket clients."""
    message = json.dumps({"type": event_type, "data": data}, default=str)
    dead = set()
    for ws in _connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


@router.websocket("/ws/incidents")
async def websocket_feed(websocket: WebSocket):
    """Live incident feed WebSocket endpoint."""
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"WS client connected. Total: {len(_connections)}")

    try:
        # Send initial connection ack
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "Connected to IMS live feed", "clients": len(_connections)}
        }))

        # Keep connection alive with ping
        while True:
            try:
                # Wait for client messages (ping/pong or disconnect)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text(json.dumps({"type": "keepalive"}))

    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        _connections.discard(websocket)
        logger.info(f"WS clients remaining: {len(_connections)}")
