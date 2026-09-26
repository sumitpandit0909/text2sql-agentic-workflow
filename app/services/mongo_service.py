from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from app.core.utils import _settings

_client : AsyncIOMotorClient | None = None

def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_settings.MONGO_URI)
    return _client

def _collection():
    return _get_client()[_settings.MONGO_DB_NAME]["chat_messages"]

async def save_turn(user_id: str, session_id: str, role: str, text: str, meta: dict | None = None) -> None:
    """Persist one message (user or agent) in a conversation thread."""
    await _collection().insert_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "role": role,  # "user" | "agent"
            "text": text,
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc),
        }
    )

async def get_history(user_id: str, session_id: str, limit: int = 10) -> list[dict]:
    """Return the most recent messages for a session, oldest first."""
    cursor = (
        _collection()
        .find({"user_id": user_id, "session_id": session_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = [doc async for doc in cursor]
    docs.reverse()
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs