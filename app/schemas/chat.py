from typing import Any, Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Stable id for the conversation thread")
    user_id: str = Field(..., description="Authenticated user id")
    message: str = Field(..., min_length=1, max_length=4000)

class ChartConfig(BaseModel):
    type: str
    labels: list[str]
    datasets: list[dict[str, Any]]

class VisualizeRequest(BaseModel):
    session_id: str
    user_id: str

class VisualizeResponse(BaseModel):
    can_visualize: bool
    chart: ChartConfig | None = None
    reason: str | None = None