
_PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]


def build_chart_config(rows:list[dict], label_key:str, value_keys: list[str],chart_type:str="bar")->dict:
    """Build a Chart.js configuration object from query result rows
    Args:
        rows: List of row dicts, e.g. the "rows" field from execute_sql's output.
        label_key: Column to use as the x-axis / category labels.
        value_keys: One or more numeric columns to plot as datasets.
        chart_type: "bar", "line", or "pie".
    Returns:
        {"suitable": True, "chart": {...Chart.js config...}} or
        {"suitable": False, "reason": "..."} when the data can't be charted
        (empty result, missing columns, or too many categories to be readable).
    """
    if not rows:
        return {"suitable": False, "reason": "The query returned no rows to chart."}

    if label_key not in rows[0] or not all(k in rows[0] for k in value_keys):
        return {"suitable": False, "reason": "Requested columns are not present in the result set."}
    
    if len(rows) > 50:
        return {"suitable": False, "reason": "Too many categories (>50) for a readable chart — try aggregating first."}
    
    labels = [str(r[label_key]) for r in rows]
    datasets = [
        {
            "label": key,
            "data": [r[key] for r in rows],
            "backgroundColor": _PALETTE[i % len(_PALETTE)],
        }
        for i, key in enumerate(value_keys)
    ]
    return {"suitable": True, "chart": {"type": chart_type, "labels": labels, "datasets": datasets}}