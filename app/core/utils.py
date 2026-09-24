from google.cloud import bigquery
from app.core.config import get_settings



_settings = get_settings()
_client: bigquery.Client | None = None

ALLOWED_TABLES ={
    "orders",
    "order_items",
    "users",
    "products",
    "inventory_items",
    "distribution_centers",
}

def _get_client()->bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(
            project=_settings.GCP_PROJECT_ID
        )
    return _client