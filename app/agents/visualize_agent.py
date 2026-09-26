from app.core.utils import _settings
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.tools.chart_tool import build_chart_config

VISUALIZE_INSTRUCTION = """
The user wants to visualize the result of their previous analytical query.
The prior result rows are available to you in session state under
`last_sql_result`.

1. Decide whether the data is chartable: it needs at least one categorical
   column and one numeric column, and a reasonable number of categories
   (roughly under 50).
2. Call build_chart_config with the label column, one or more numeric
   columns, and the best chart type ("bar" for comparisons/categories,
   "line" for a time series, "pie" only for a small part-to-whole set).
3. If build_chart_config says the data isn't suitable, explain briefly and
   concretely why (e.g. too many categories, no numeric column, no data),
   and suggest how the user could adjust their question to make it
   chartable.
4. If it is suitable, confirm to the user that the chart is ready — the
   frontend renders the actual chart from the returned config, you do not
   need to describe every data point in text.
"""

visualize_agent = LlmAgent(
    name="visualize_agent",
    model=LiteLlm(model=_settings.SYNTHESIS_MODEL),
    description="Builds a Chart.js configuration from the previous query's results when the user explicitly asks to see a chart.",
    instruction=VISUALIZE_INSTRUCTION,
    tools=[build_chart_config],
    output_key="last_chart_result",
)