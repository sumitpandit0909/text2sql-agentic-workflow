from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from collections.abc import AsyncIterator
from app.agents.root_agent import root_agent

APP_NAME = "thelook_genai_agent"


_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent,app_name=APP_NAME,session_service=_session_service)

async def ensure_session(user_id:str,session_id:str)->None:
    """Create the ADK session if it doesn't exist yet (idempotent)."""
    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

async def stream_agent_reply(user_id:str,session_id:str,message:str)->AsyncIterator[str]:
    """Run one turn of the agent, yielding text chunks as they're produced.
    """
    await ensure_session(user_id,session_id)
    content =types.Content(role="user", parts=[types.Part(text=message)])

    async for event in _runner.run_async(
        user_id=user_id,session_id=session_id,new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text


async def get_session_state(user_id: str, session_id: str) -> dict:
    """Read back session state (e.g. last_sql_result) for /visualize."""
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return dict(session.state) if session else {}