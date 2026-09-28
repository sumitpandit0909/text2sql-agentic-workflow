import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services import mongo_service
from app.services.runner_service import stream_agent_reply

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    await mongo_service.save_turn(req.user_id, req.session_id, "user", req.message)

    async def event_stream():
        answer_chunks: list[str] = []
        meta: dict = {}
        async for event in stream_agent_reply(req.user_id, req.session_id, req.message):
            yield json.dumps(event) + "\n"
            if event["type"] == "text":
                answer_chunks.append(event["content"])
            elif event["type"] == "answer":
                d = event["data"]
                answer_chunks.append(d.get("answer") or d.get("summary") or d.get("message") or "")
                meta = {"workflow": event["workflow"], **d}
        await mongo_service.save_turn(req.user_id, req.session_id, "agent", "".join(answer_chunks), meta)

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")