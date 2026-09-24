from app.core.utils import _get_client, _settings

def run_ai_forecast(metric_table: str,timestamp_col:str,value_col:str, horizon:int=30)->dict:
    """Forecast a time-series metric using BigQuery ML's AI.FORECAST.

    Args:
        metric_table: Bare table name to aggregate and forecast from
            (e.g. "order_items" for revenue, "orders" for order volume).
        timestamp_col: Name of the date/timestamp column to bucket by day.
        value_col: Name of the numeric column to sum per day before forecasting.
            Pass "*" to forecast a daily COUNT(*) instead of a SUM.
        horizon: Number of future days to forecast (default 30).
    Returns:
            {"forecast": [{"date": ..., "value": ..., "lower": ..., "upper": ...}, ...]}
        on success, or {"error": "..."} on failure.
    """
    agg = "COUNT(*)" if value_col == "*" else f"SUM({value_col})"
    history_sql= f"""
        WITH daily AS (
          SELECT DATE({timestamp_col}) AS ds, {agg} AS y
          FROM `{_settings.BQ_DATASET}.{metric_table}`
          GROUP BY ds
        )
        SELECT * FROM AI.FORECAST(
          TABLE daily,
          horizon => {int(horizon)},
          timestamp_col => 'ds',
          data_col => 'y'
        )
    """

    client =_get_client()
    try:
        rows=[dict(r) for r in client.query(history_sql).result()]
        forecast=[
            {
                "date": str(r.get("forecast_timestamp")),
                "value": r.get("forecast_value"),
                "lower": r.get("prediction_interval_lower_bound"),
                "upper": r.get("prediction_interval_upper_bound"),
            }
            for r in rows
        ]

        return {"forecast":forecast}

    except Exception as exc:
        return {"error":f"BigQuery forecast error: {exc}"}
