from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_chat import router as chat_router
from app.core.observability import setup_observability


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_observability()
    yield


app = FastAPI(title="TheLook GenAI Data Intelligence Agent", lifespan=lifespan)

app.include_router(chat_router, tags=["chat"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}