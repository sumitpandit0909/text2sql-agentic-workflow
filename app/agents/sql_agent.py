from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools import exit_loop
from google.adk.tools.toolbox_toolset import ToolboxToolset
from google.adk.models.lite_llm import LiteLlm

from app.core.utils import _settings
from app.schemas.agent_outputs import SqlAnswer
from app.prompts.sql_prompts import (
    SQL_WORKER_INSTRUCTION,
    SQL_CHECK_INSTRUCTION,
    SQL_SYNTHESIS_INSTRUCTION,
)
from app.tools.mcp_callbacks import (
    validate_sql_before_tool,
    handle_sql_result_after_tool,
)

# 1. MCP Toolbox integration
toolbox_toolset = ToolboxToolset(
    server_url=_settings.TOOLBOX_URL,
    tool_names=["execute_sql"],
)

# 2. SQL Worker Agent (Writes and executes BigQuery SQL)
sql_worker_agent = LlmAgent(
    name="sql_worker_agent",
    model=LiteLlm(model=_settings.SQL_MODEL),
    description="Generates and executes BigQuery SQL for TheLook e-commerce questions via MCP Toolbox.",
    instruction=SQL_WORKER_INSTRUCTION,
    tools=[toolbox_toolset],
    before_tool_callback=validate_sql_before_tool,
    after_tool_callback=handle_sql_result_after_tool,
)

# 3. SQL Check Agent (Verifies execution success or prompts retry)
sql_check_agent = LlmAgent(
    name="sql_check_agent",
    model=LiteLlm(model=_settings.ROUTER_MODEL),
    description="Checks whether the last SQL execution succeeded and exits the retry loop if so.",
    instruction=SQL_CHECK_INSTRUCTION,
    tools=[exit_loop],
)

# 4. Self-Correction Retry Loop (LoopAgent)
sql_retry_loop = LoopAgent(
    name="sql_retry_loop",
    sub_agents=[sql_worker_agent, sql_check_agent],
    max_iterations=_settings.MAX_SQL_RETRIES,
)

# 5. SQL Synthesis Agent (Generates direct natural-language SqlAnswer)
sql_synthesis_agent = LlmAgent(
    name="sql_synthesis_agent",
    model=LiteLlm(model=_settings.SYNTHESIS_MODEL),
    output_schema=SqlAnswer,
    description="Synthesizes the final natural-language answer from the SQL retry loop's result.",
    instruction=SQL_SYNTHESIS_INSTRUCTION,
)

# 6. Composite SQL Agent (Sequential execution: Loop -> Synthesis)
sql_agent = SequentialAgent(
    name="sql_agent",
    description=(
        "Answers analytical questions about TheLook e-commerce data "
        "(revenue, orders, users, inventory) by generating and running "
        "validated BigQuery SQL, with a bounded self-correction loop."
    ),
    sub_agents=[sql_retry_loop, sql_synthesis_agent],
)