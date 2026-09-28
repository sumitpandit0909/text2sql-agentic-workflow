"""
Tool callbacks for MCP Toolbox execute_sql integration:
- before_tool_callback: Validates safety (read-only, DDL/DML rejection, LIMIT bounds).
- after_tool_callback: Normalizes JSON result and stores in tool_context.state for charts and verification.
"""

import json
from app.core.utils import _settings
from app.tools.bigquery_tool import validate_sql


def validate_sql_before_tool(tool, args, tool_context):
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


def handle_sql_result_after_tool(tool, args, tool_context, response):
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
