VISUALIZE_INSTRUCTION = """
The user wants to visualize analytical or forecast data from the prior step.
The previous result rows are automatically retrieved by `build_chart_config` from session state.

1. Review the data discussed in the conversation.
2. Call `build_chart_config` with:
   - `label_key`: The exact column name to use as x-axis/category labels (e.g. 'category', 'date', 'country').
   - `value_keys`: List containing numeric column names to plot (e.g. ['total_revenue'], ['value'], ['total_orders']).
   - `chart_type`: Best chart type ("bar" for comparisons/categories, "line" for dates/time-series, "pie" only for small proportions <= 6).
   Do NOT pass the rows parameter manually; the tool loads them directly from the prior query in session state.
3. If build_chart_config returns suitable=true:
   - set chart_ready=True
   - set message to a concise confirmation, e.g. "Here is the bar chart showing sales revenue by category."
4. If build_chart_config returns suitable=false:
   - set chart_ready=False
   - set message explaining clearly why it cannot be charted and suggest how to adjust the query.
"""
