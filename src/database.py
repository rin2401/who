from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_db]
    print("✅ Connected to MongoDB")


async def close_db():
    global _client
    if _client:
        _client.close()


def get_db():
    return _db
