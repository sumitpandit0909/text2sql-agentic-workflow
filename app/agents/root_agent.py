from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agents.forecast_agent import forecast_agent
from app.agents.sql_agent import sql_agent
from app.agents.visualize_agent import visualize_agent
from app.core.utils import _settings
from app.prompts.router_prompts import ROUTER_INSTRUCTION

root_agent = LlmAgent(
    name="root_agent",
    model=LiteLlm(model=_settings.ROUTER_MODEL),
    description="Top-level router for the TheLook Data Intelligence Agent.",
    instruction=ROUTER_INSTRUCTION,
    sub_agents=[sql_agent, forecast_agent, visualize_agent],
)