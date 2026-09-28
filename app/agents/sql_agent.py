import json
from pathlib import Path
import logging

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools import exit_loop
from google.adk.tools.toolbox_toolset import ToolboxToolset
from google.adk.models.lite_llm import LiteLlm

from app.core.utils import _settings
from app.tools.bigquery_tool import validate_sql
from app.schemas.agent_outputs import SqlAnswer


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

def _validate_sql_before_tool(tool, args, tool_context):
    """Enforce security and safety validation before the MCP tool executes."""
    if tool.name == "execute_sql":
        sql = args.get("sql", "")
        ok, reason = validate_sql(sql)
        if not ok:
            return {"error": f"Validation failed: {reason}"}
        # Auto-append LIMIT clause if missing
        bounded_sql = sql.rstrip(";")
        if "limit" not in bounded_sql.lower():
            args["sql"] = f"{bounded_sql} LIMIT {_settings.MAX_ROWS_RETURNED}"
    return None

def _handle_sql_result_after_tool(tool, args, tool_context, response):
    """Normalize MCP Toolbox response and preserve rows in state for charts and loop check."""
    if tool.name == "execute_sql":
        raw_res = response.get("result") if isinstance(response, dict) else response
        if isinstance(raw_res, str):
            try:
                parsed = json.loads(raw_res)
                if isinstance(parsed, dict):
                    rows = [parsed]
                elif isinstance(parsed, list):
                    rows = parsed
                else:
                    rows = [{"result": parsed}]
                tool_context.state["last_sql_result"] = {
                    "rows": rows,
                    "row_count": len(rows),
                    "sql_executed": args.get("sql", ""),
                }
            except Exception:
                tool_context.state["last_sql_result"] = {"error": raw_res}
        elif isinstance(raw_res, list):
            tool_context.state["last_sql_result"] = {
                "rows": raw_res,
                "row_count": len(raw_res),
                "sql_executed": args.get("sql", ""),
            }
        elif isinstance(raw_res, dict):
            if "rows" in raw_res:
                tool_context.state["last_sql_result"] = raw_res
            else:
                tool_context.state["last_sql_result"] = {
                    "rows": [raw_res],
                    "row_count": 1,
                    "sql_executed": args.get("sql", ""),
                }
    return None

toolbox_toolset = ToolboxToolset(
    server_url=_settings.TOOLBOX_URL,
    tool_names=["execute_sql"],
)

SQL_WORKER_INSTRUCTION = f"""
You are the Text-to-SQL worker for TheLook E-commerce BigQuery dataset.

Schema reference — use it instead of guessing column names or enum values:
{_SCHEMA_REFERENCE}

Workflow:
1. Write a single BigQuery Standard SQL SELECT statement that answers the user's question using the schema reference above.
2. Call `execute_sql` with that statement.
3. If `execute_sql` returned an error on a previous attempt (visible in your conversation history), read it and try a corrected query.
4. `bigquery-public-data.thelook_ecommerce` is the dataset name. Always prefix table names with the dataset name (e.g. `bigquery-public-data.thelook_ecommerce.orders`).
Never write anything other than SELECT/WITH queries.

Do not write a natural-language summary or final answer yourself — your only job is to get a successful query result into state. The synthesis step downstream will write the user-facing answer.
"""

sql_worker_agent = LlmAgent(
    name="sql_worker_agent",
    model=LiteLlm(model=_settings.SQL_MODEL),
    description="Generates and executes BigQuery SQL for TheLook e-commerce questions via MCP Toolbox.",
    instruction=SQL_WORKER_INSTRUCTION,
    tools=[toolbox_toolset],
    before_tool_callback=_validate_sql_before_tool,
    after_tool_callback=_handle_sql_result_after_tool,
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
You write the final answer for a data question. Use ONLY the results of
the execute_sql tool calls visible in this conversation.

- If the last execute_sql call succeeded: status="success". Fill `answer`
  with a direct 1-4 sentence answer, `key_figures` with the important
  numbers (label + value as returned), `sql` with the exact SQL that ran
  (the "sql_executed" value), and `row_count`.
- If no execute_sql call succeeded: status="failed", give `failure_reason`
  in plain language (never a stack trace), and set `sql`/`row_count` to null.

Never invent numbers.
"""

sql_synthesis_agent = LlmAgent(
    name="sql_synthesis_agent",
    model=LiteLlm(model=_settings.SYNTHESIS_MODEL),
    output_schema=SqlAnswer,
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