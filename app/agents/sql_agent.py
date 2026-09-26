from pathlib import Path
import logging

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools import exit_loop
from google.adk.models.lite_llm import LiteLlm

from app.core.utils import _settings
from app.tools.bigquery_tool import ALLOWED_TABLES, discover_schema, execute_sql


logger = logging.getLogger(__name__)

def _load_schema_reference() -> str:
    schema_path = Path(__file__).resolve().parents[1] / "docs" / "table_schema.md"
    try:
        content = schema_path.read_text(encoding="utf-8")
        logger.info("Loaded schema reference from %s (%d chars)", schema_path, len(content))
        return content
    except FileNotFoundError:
        logger.warning("Schema reference not found at %s — agent will rely on discover_schema tool only.", schema_path)
        return ""

_SCHEMA_REFERENCE = _load_schema_reference()

SQL_WORKER_INSTRUCTION = f"""
You are the Text-to-SQL worker for TheLook E-commerce BigQuery dataset.

Schema reference — use it instead of guessing column names or enum values.:

{_SCHEMA_REFERENCE}

1. Write a single BigQuery Standard SQL SELECT statement that answers the
   user's question.
2. Call execute_sql with that statement.
3. If execute_sql returned an "error" on a previous attempt (visible in
   your conversation history), read it and try a corrected query.
4.`bigquery-public-data.thelook_ecommerce` is the dataset name after this you can sufffix the table name followed by dot.
Never write anything other than SELECT/WITH queries.

Do not write a natural-language summary or final answer yourself — your
only job is to get a successful query result into state. The synthesis
step downstream will write the user-facing answer
"""

sql_worker_agent = LlmAgent(
    name="sql_worker_agent",
    model=LiteLlm(model=_settings.SQL_MODEL),
    description="Generates and executes BigQuery SQL for TheLook e-commerce questions.",
    instruction=SQL_WORKER_INSTRUCTION,
    tools=[execute_sql],
    output_key="last_sql_result",
)

SQL_CHECK_INSTRUCTION = """
Look at the value in state key `last_sql_result`.

If it contains a "rows" key (the query succeeded), call the exit_loop
tool immediately and say nothing else.

If it contains an "error" key, do not call any tool — just respond with
the single word "retry".
"""

sql_check_agent = LlmAgent(
    name="sql_check_agent",
    model=LiteLlm(model=_settings.ROUTER_MODEL),
    description="Checks whether the last SQL execution succeeded and exits the retry loop if so.",
    instruction=SQL_CHECK_INSTRUCTION,
    tools=[exit_loop],
)

sql_retry_loop = LoopAgent(
    name="sql_retry_loop",
    sub_agents=[sql_worker_agent, sql_check_agent],
    max_iterations=_settings.MAX_SQL_RETRIES,
)


SQL_SYNTHESIS_INSTRUCTION = """
Look at state key `last_sql_result`.

If it has a "rows" key, synthesize a clear natural-language answer to the
original question using only those numbers, and include the SQL from its
"sql_executed" field.

If it still has an "error" key, tell the user plainly that the query
could not be completed and briefly say why — never expose raw stack
traces.
"""

sql_synthesis_agent = LlmAgent(
    name="sql_synthesis_agent",
    model=LiteLlm(model=_settings.SYNTHESIS_MODEL),
    description="Synthesizes the final natural-language answer from the SQL retry loop's result.",
    instruction=SQL_SYNTHESIS_INSTRUCTION,
)


sql_agent = SequentialAgent(
    name="sql_agent",
    description=(
        "Answers analytical questions about TheLook e-commerce data "
        "(revenue, orders, users, inventory) by generating and running "
        "validated BigQuery SQL, with a bounded self-correction loop."
    ),
    sub_agents=[sql_retry_loop, sql_synthesis_agent],
)