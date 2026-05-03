from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.MONGO_DB]


async def init_mongo() -> None:
    db = get_mongo_db()
    # Create indexes for efficient querying
    await db.signals.create_index([("work_item_id", 1)])
    await db.signals.create_index([("component_id", 1)])
    await db.signals.create_index([("timestamp", -1)])
    await db.signals.create_index([("component_id", 1), ("timestamp", -1)])


async def close_mongo() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
