from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.core.utils import _settings
from app.tools.forecast_tool import run_ai_forecast


FORECAST_INSTRUCTION = """
You forecast e-commerce time-series metrics (revenue, order volume, signups)
for TheLook E-commerce using BigQuery ML's AI.FORECAST.

1. Identify which table/column combination the user's metric maps to, e.g.
   revenue -> order_items.sale_price summed by created_at; order volume ->
   orders count by created_at.
2. Call run_ai_forecast with that table, timestamp column, value column,
   and a sensible horizon (default 30 days unless the user asks otherwise).
3. If it returns an error, explain in plain language what went wrong —
   never expose raw stack traces.
4. On success, explain the forecast in natural language: the overall trend,
   the forecasted values for a few key checkpoints, and the uncertainty
   range. Do not just repeat the raw numbers back.
"""

forecast_agent = LlmAgent(
    name="forecast_agent",
    model=LiteLlm(model=_settings.FORECAST_MODEL),
    description="Produces and explains time-series forecasts (e.g. 'forecast sales for next month') using BigQuery ML AI.FORECAST.",
    instruction=FORECAST_INSTRUCTION,
    tools=[run_ai_forecast],
    output_key="last_forecast_result",
)