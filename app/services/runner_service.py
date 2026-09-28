from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import json
from collections.abc import AsyncIterator
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models.lite_llm import LiteLlm

from app.agents.root_agent import root_agent
from app.core.utils import _settings
from app.schemas.agent_outputs import ChartAnswer, ForecastAnswer, SqlAnswer

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
_AGENT_STATUS_MESSAGES = {
    "sql_worker_agent": "Analyzing your question and writing SQL...",
    "sql_synthesis_agent": "Writing your answer...",
    "forecast_agent": "Working on your forecast...",
    "visualize_agent": "Preparing your chart...",
}
_OUTPUT_MODELS = {
    "sql_synthesis_agent": ("sql", SqlAnswer),
    "forecast_agent": ("forecast", ForecastAnswer),
    "visualize_agent": ("chart", ChartAnswer),
}
_FINAL_ANSWER_AGENTS = {"root_agent", "sql_synthesis_agent", "forecast_agent", "visualize_agent"}

async def stream_agent_reply(user_id: str, session_id: str, message: str) -> AsyncIterator[dict]:
    await ensure_session(user_id, session_id)
    content = types.Content(role="user", parts=[types.Part(text=message)])

    seen_authors: set[str] = set()
    sql_attempt = 0

    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # 1. Agent-transition status — ek baar per agent
        status_msg = _AGENT_STATUS_MESSAGES.get(event.author)
        if status_msg and event.author not in seen_authors:
            seen_authors.add(event.author)
            yield {"type": "status", "message": status_msg}

        # 2. Tool-call preview
        for call in event.get_function_calls():
            if call.name == "transfer_to_agent":
                target = call.args.get("agent_name", "specialist")
                yield {"type": "status", "message": f"Routing to {target}..."}
            elif call.name == "execute_sql":
                sql_attempt += 1
                # sql_preview = (call.args.get("sql") or "")[:200]
                label = "Running SQL" if sql_attempt == 1 else f"Retrying (attempt {sql_attempt})"
                yield {"type": "status", "message": f"{label}"}
            elif call.name == "discover_schema":
                yield {"type": "status", "message": "Looking up table schema..."}
            elif call.name == "run_ai_forecast":
                yield {"type": "status", "message": "Running forecast model..."}
            elif call.name == "build_chart_config":
                yield {"type": "status", "message": "Building chart..."}

        # 3. Tool-result feedback — success/error turant dikhao
        for response in event.get_function_responses():
            if response.name == "execute_sql":
                if "error" in response.response:
                    reason = str(response.response["error"])[:150]
                    yield {"type": "status", "message": f"Query failed — {reason}. Retrying..."}
                elif "rows" in response.response:
                    yield {"type": "status", "message": f"Query succeeded ({response.response.get('row_count', 0)} rows)."}
            elif response.name == "run_ai_forecast":
                if "error" in response.response:
                    reason = str(response.response["error"])[:150]
                    yield {"type": "status", "message": f"Forecast failed — {reason}."}
                else:
                    yield {"type": "status", "message": "Forecast generated."}
            elif response.name == "build_chart_config":
                if response.response.get("suitable"):
                    yield {"type": "chart", "chart": response.response["chart"]}
                else:
                    yield {"type": "status", "message": response.response.get("reason", "Chart not suitable.")}

        # 4. Final answer
        if event.author in _FINAL_ANSWER_AGENTS and event.content and event.content.parts:
            for part in event.content.parts:
                if not part.text:
                    continue
                if event.author in _OUTPUT_MODELS:
                    workflow, model = _OUTPUT_MODELS[event.author]
                    try:
                        data = model.model_validate_json(part.text).model_dump()
                        yield {"type": "answer", "workflow": workflow, "data": data}
                        continue
                    except Exception:
                        pass  # schema parse fail: neeche plain text ki tarah bhej do
                yield {"type": "text", "content": part.text}

async def get_session_state(user_id: str, session_id: str) -> dict:
    """Read back session state — e.g. for debugging or future features."""
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return dict(session.state) if session else {}