from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.core.utils import _settings
from app.tools.chart_tool import build_chart_config
from app.schemas.agent_outputs import ChartAnswer
from app.prompts.visualize_prompts import VISUALIZE_INSTRUCTION

visualize_agent = LlmAgent(
    name="visualize_agent",
    model=LiteLlm(model=_settings.SYNTHESIS_MODEL),
    output_schema=ChartAnswer,
    description="Builds a Chart.js configuration from the previous query's results when the user explicitly asks to see a chart.",
    instruction=VISUALIZE_INSTRUCTION,
    tools=[build_chart_config],
    output_key="last_chart_result",
)