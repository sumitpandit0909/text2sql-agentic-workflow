import logging
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing_extensions import override

from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.platform import time as platform_time
from google.adk.platform import uuid as platform_uuid
from google.adk.sessions._session_util import decode_model, make_json_safe_state

logger = logging.getLogger(__name__)


class MongoSessionService(BaseSessionService):
    """MongoDB implementation of Google ADK BaseSessionService.
    
    Persists ADK sessions, state dictionaries, and event sequences to MongoDB,
    enabling stateless FastAPI/ADK backends that survive restarts and scale across
    multiple processes/containers.
    """

    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_uri)
        self._db: AsyncIOMotorDatabase = self._client[db_name]
        self._sessions_col = self._db["adk_sessions"]
        self._events_col = self._db["adk_session_events"]
        self._indexes_created = False

    async def _ensure_indexes(self) -> None:
        if not self._indexes_created:
            try:
                await self._sessions_col.create_index([("app_name", 1), ("user_id", 1), ("last_update_time", 1)])
                await self._events_col.create_index([("session_key", 1), ("timestamp", 1)])
                self._indexes_created = True
            except Exception as e:
                logger.warning("Failed to create MongoDB session indexes: %s", e)

    @staticmethod
    def _make_key(app_name: str, user_id: str, session_id: str) -> str:
        return f"{app_name}:{user_id}:{session_id}"

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        await self._ensure_indexes()
        sid = (session_id or "").strip() or platform_uuid.new_uuid()
        key = self._make_key(app_name, user_id, sid)

        existing = await self._sessions_col.find_one({"_id": key})
        if existing:
            raise AlreadyExistsError(f"Session with id {sid} already exists for user {user_id}.")

        now = platform_time.get_time()
        safe_state = make_json_safe_state(state or {})

        doc = {
            "_id": key,
            "id": sid,
            "app_name": app_name,
            "user_id": user_id,
            "state": safe_state,
            "last_update_time": now,
        }
        await self._sessions_col.insert_one(doc)

        return Session(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=safe_state,
            events=[],
            last_update_time=now,
        )

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        await self._ensure_indexes()
        key = self._make_key(app_name, user_id, session_id)
        doc = await self._sessions_col.find_one({"_id": key})
        if not doc:
            return None

        # Build events query
        query: dict[str, Any] = {"session_key": key}
        if config and config.after_timestamp is not None:
            query["timestamp"] = {"$gte": config.after_timestamp}

        num_recent = config.num_recent_events if config else None

        if num_recent == 0:
            events = []
        elif num_recent is not None and num_recent > 0:
            # Fetch recent events descending, then reverse to chronological order
            cursor = self._events_col.find(query).sort("timestamp", -1).limit(num_recent)
            raw_docs = [d async for d in cursor]
            raw_docs.reverse()
            events = []
            for d in raw_docs:
                ev = decode_model(d.get("event_data"), Event)
                if ev is not None:
                    events.append(ev)
        else:
            cursor = self._events_col.find(query).sort("timestamp", 1)
            raw_docs = [d async for d in cursor]
            events = []
            for d in raw_docs:
                ev = decode_model(d.get("event_data"), Event)
                if ev is not None:
                    events.append(ev)

        return Session(
            id=doc.get("id", session_id),
            app_name=doc.get("app_name", app_name),
            user_id=doc.get("user_id", user_id),
            state=doc.get("state", {}),
            events=events,
            last_update_time=doc.get("last_update_time", 0.0),
        )

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        await self._ensure_indexes()
        query: dict[str, Any] = {"app_name": app_name}
        if user_id:
            query["user_id"] = user_id

        cursor = self._sessions_col.find(query).sort("last_update_time", 1)
        sessions = [
            Session(
                id=d.get("id", ""),
                app_name=d.get("app_name", app_name),
                user_id=d.get("user_id", ""),
                state=d.get("state", {}),
                events=[],
                last_update_time=d.get("last_update_time", 0.0),
            )
            async for d in cursor
        ]
        return ListSessionsResponse(sessions=sessions)

    @override
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        key = self._make_key(app_name, user_id, session_id)
        await self._sessions_col.delete_one({"_id": key})
        await self._events_col.delete_many({"session_key": key})

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        if event.partial:
            return event

        self._apply_temp_state(session, event)
        event = self._trim_temp_delta_state(event)
        self._update_session_state(session, event)
        session.events.append(event)

        now = event.timestamp or platform_time.get_time()
        session.last_update_time = now

        key = self._make_key(session.app_name, session.user_id, session.id)
        safe_state = make_json_safe_state(session.state)
        event_dict = event.model_dump(mode="json")

        await self._events_col.update_one(
            {"_id": event.id},
            {
                "$set": {
                    "session_key": key,
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "session_id": session.id,
                    "timestamp": now,
                    "event_data": event_dict,
                }
            },
            upsert=True,
        )

        await self._sessions_col.update_one(
            {"_id": key},
            {
                "$set": {
                    "state": safe_state,
                    "last_update_time": now,
                    "id": session.id,
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                }
            },
            upsert=True,
        )

        return event

    @override
    async def flush(self) -> None:
        pass
