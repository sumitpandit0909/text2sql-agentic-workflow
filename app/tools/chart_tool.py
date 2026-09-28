
from google.adk.tools import ToolContext

_PALETTE = [
    "#6366F1",  # Indigo
    "#06B6D4",  # Cyan
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#8B5CF6",  # Purple
    "#3B82F6",  # Blue
    "#14B8A6",  # Teal
    "#F97316",  # Orange
    "#E11D48",  # Rose
]


def build_chart_config(
    label_key: str,
    value_keys: list[str],
    chart_type: str = "bar",
    rows: list[dict] | None = None,
    tool_context: ToolContext | None = None,
) -> dict:
    """Build a Chart.js configuration object from query result rows.

    Args:
        label_key: Column name to use as the x-axis / category labels.
        value_keys: One or more numeric column names to plot as datasets.
        chart_type: "bar", "line", or "pie".
        rows: Optional list of row dicts. If omitted, the rows from the most recent
            SQL query in session state are used automatically.
        tool_context: Injected by Google ADK framework to access session state.

    Returns:
        {"suitable": True, "chart": {...Chart.js config...}} or
        {"suitable": False, "reason": "..."} when the data can't be charted
        (empty result, missing columns, or too many categories to be readable).
    """
    if not rows and tool_context is not None:
        sql_res = tool_context.state.get("last_sql_result")
        if isinstance(sql_res, str):
            try:
                import json
                sql_res = json.loads(sql_res)
            except Exception:
                pass
        if isinstance(sql_res, dict) and "rows" in sql_res:
            rows = sql_res["rows"]
        elif isinstance(sql_res, list):
            rows = sql_res
        elif isinstance(sql_res, dict):
            rows = [sql_res]

    if not rows:
        return {"suitable": False, "reason": "The query returned no rows to chart."}

    if label_key not in rows[0] or not all(k in rows[0] for k in value_keys):
        available = list(rows[0].keys())
        return {
            "suitable": False,
            "reason": f"Requested columns not found in data. Available columns are: {', '.join(available)}",
        }
    
    if len(rows) > 50:
        return {"suitable": False, "reason": "Too many categories (>50) for a readable chart — try aggregating first."}
    
    labels = [str(r[label_key]) for r in rows]
    datasets = []

    for i, key in enumerate(value_keys):
        dataset = {
            "label": key,
            "data": [r[key] for r in rows],
        }

        if chart_type in ("pie", "doughnut"):
            # Each pie slice represents a category, so it must have a distinct color
            dataset["backgroundColor"] = [
                _PALETTE[j % len(_PALETTE)] for j in range(len(rows))
            ]
            dataset["borderColor"] = "#161922"
            dataset["borderWidth"] = 2
        elif chart_type == "line":
            color = _PALETTE[i % len(_PALETTE)]
            dataset["borderColor"] = color
            dataset["backgroundColor"] = color + "26"  # 15% opacity fill
            dataset["tension"] = 0.35
            dataset["fill"] = True
            dataset["pointRadius"] = 4
        else:  # bar
            # Single uniform color per metric series (clean, non-rainbow bars)
            dataset["backgroundColor"] = _PALETTE[i % len(_PALETTE)]
            dataset["borderRadius"] = 6

        datasets.append(dataset)

    return {"suitable": True, "chart": {"type": chart_type, "labels": labels, "datasets": datasets}}