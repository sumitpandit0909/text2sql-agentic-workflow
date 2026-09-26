from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from collections.abc import AsyncIterator
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models.lite_llm import LiteLlm

from app.agents.root_agent import root_agent
from app.core.utils import _settings

APP_NAME = "thelook_genai_agent"

app = App(
    name=APP_NAME,
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,   # har 3 invocations ke baad purani history summarize ho jayegi
        overlap_size=1,          # pichli window ka last invocation continuity ke liye retain rahega
        summarizer=LlmEventSummarizer(llm=LiteLlm(model=_settings.ROUTER_MODEL)),  # cheap model summarize ke liye
    ),
)
_session_service = InMemorySessionService()
_runner = Runner(app=app,session_service=_session_service)

async def ensure_session(user_id:str,session_id:str)->None:
    """Create the ADK session if it doesn't exist yet (idempotent)."""
    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

_TOOL_STATUS_MESSAGES = {
    "discover_schema": "Looking up table schema...",
    "execute_sql": "Running SQL query...",
    "run_ai_forecast": "Generating forecast...",
    "build_chart_config": "Building chart...",
}

_FINAL_ANSWER_AGENTS = {"root_agent", "sql_synthesis_agent", "forecast_agent", "visualize_agent"}

async def stream_agent_reply(user_id: str, session_id: str, message: str) -> AsyncIterator[dict]:
    await ensure_session(user_id, session_id)
    content = types.Content(role="user", parts=[types.Part(text=message)])

    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # Tool-call status updates (jo humne pehle discuss kiya)
        for call in event.get_function_calls():
            if call.name == "transfer_to_agent":
                yield {"type": "status", "message": "Routing your question..."}
            elif call.name in _TOOL_STATUS_MESSAGES:
                yield {"type": "status", "message": _TOOL_STATUS_MESSAGES[call.name]}

        # Chart config seedha detect karo jab build_chart_config return kare
        for response in event.get_function_responses():
            if response.name == "build_chart_config" and response.response.get("suitable"):
                yield {"type": "chart", "chart": response.response["chart"]}

        # Final-answer text
        if event.author in _FINAL_ANSWER_AGENTS and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield {"type": "text", "content": part.text}
async def get_session_state(user_id: str, session_id: str) -> dict:
    """Read back session state — e.g. for debugging or future features."""
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return dict(session.state) if session else {}