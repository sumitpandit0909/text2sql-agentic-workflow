from app.agents.sql_agent import sql_agent
from app.agents.forecast_agent import forecast_agent
from app.agents.visualize_agent import visualize_agent
from app.agents.root_agent import root_agent
# python -c "from app.tools.forecast_tools import run_ai_forecast; print(run_ai_forecast('orders', 'created_at', '*', horizon=7))"
if __name__ == "__main__":
    print(sql_agent.name, sql_agent.model)
    print(forecast_agent.name, forecast_agent.model)
    print(visualize_agent.name, visualize_agent.model)
    print(root_agent.name, [a.name for a in root_agent.sub_agents])