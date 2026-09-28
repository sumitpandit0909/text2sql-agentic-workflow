from typing import Literal
from pydantic import BaseModel, Field


class KeyFigure(BaseModel):
    label: str = Field(description="What the number represents, e.g. 'Total orders in 2023'.")
    value: str = Field(description="The figure exactly as returned by the tool, formatted for reading, e.g. '13,935' or '$1,119,967.55'.")


class SqlAnswer(BaseModel):
    status: Literal["success", "failed"] = Field(description="'success' only if a query ran successfully and returned data.")
    answer: str = Field(description="Direct natural-language answer in 1-4 sentences. Do not put SQL here.")
    key_figures: list[KeyFigure] = Field(default_factory=list, description="Up to 10 most important figures from the result. Empty list if not numeric.")
    sql: str | None = Field(default=None, description="The exact final SQL that was executed, or null if no query succeeded.")
    row_count: int | None = Field(default=None, description="Rows returned by the executed query, or null.")
    failure_reason: str | None = Field(default=None, description="Plain-language reason, only when status is 'failed'. Never a stack trace. Otherwise null.")


class ForecastPoint(BaseModel):
    date: str = Field(description="Forecast date, YYYY-MM-DD.")
    value: float
    lower: float = Field(description="Lower bound of the prediction interval.")
    upper: float = Field(description="Upper bound of the prediction interval.")


class ForecastAnswer(BaseModel):
    status: Literal["success", "failed"]
    summary: str = Field(description="Plain-language explanation of the forecast: trend and uncertainty.")
    trend: Literal["up", "down", "flat"] | None = Field(default=None, description="Overall direction, or null if failed.")
    horizon_days: int | None = Field(default=None, description="Number of days forecasted, or null.")
    checkpoints: list[ForecastPoint] = Field(default_factory=list, description="3-7 representative points copied from the tool result. Empty if failed.")
    failure_reason: str | None = Field(default=None, description="Plain-language reason if failed, else null.")


class ChartAnswer(BaseModel):
    chart_ready: bool = Field(description="True only if build_chart_config returned suitable=true.")
    message: str = Field(description="One or two sentences for the user. If not chartable, say why and how to rephrase.")