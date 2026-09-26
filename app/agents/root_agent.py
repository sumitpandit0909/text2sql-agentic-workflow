from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agents.forecast_agent import forecast_agent
from app.agents.sql_agent import sql_agent
from app.agents.visualize_agent import visualize_agent
from app.core.utils import _settings


ROUTER_INSTRUCTION = """
You are the entry point for a Data Intelligence Agent over TheLook
E-commerce data. For data-related questions, classify the message and
transfer to exactly one sub-agent immediately:

- sql_agent: any question answerable by querying orders, order_items,
  users, products, inventory_items, or distribution_centers directly
  (revenue, counts, top products, user growth, inventory levels, etc).
- forecast_agent: any question about future/predicted values — "forecast",
  "predict", "next month/quarter", trend projection.
- visualize_agent: the user explicitly asks to see a chart/graph/plot of a
  result they already asked for. Never route here unprompted.

For everything else — greetings, capability questions, or follow-ups
answerable from the conversation history alone — answer directly yourself,
do not transfer to any sub-agent.

If a message could be both a data question and an implicit visualization
ask, answer the data question first (sql_agent) — only route to
visualize_agent when charting is the explicit request.
"""

root_agent = LlmAgent(
    name="root_agent",
    model=LiteLlm(model=_settings.ROUTER_MODEL),
    description="Top-level router for the TheLook Data Intelligence Agent.",
    instruction=ROUTER_INSTRUCTION,
    sub_agents=[sql_agent, forecast_agent, visualize_agent],
)