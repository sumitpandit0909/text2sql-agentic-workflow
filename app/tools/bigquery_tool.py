import re
from google.cloud import bigquery
from app.core.config import get_settings
from app.core.utils import _get_client
from app.core.utils import ALLOWED_TABLES
_settings = get_settings()


_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|CREATE|GRANT)\b",
    re.IGNORECASE
)


def discover_schema(table_name:list[str])->dict:
    """Look up tables name and types  for the look e-commerce tables.

    Call this before writing SQL so column names are never guessed.

    Args:
        table_name: names of the tables you want to discover

    Returns:
        dict mapping each table name to a list of (column, type) pairs

    """
    client = _get_client()
    result:dict ={}

    for name in table_name:
        if name not in ALLOWED_TABLES:
            result[name]= {"error":f"'{name}' is not an allowed table"}
            continue
        try:
            table = client.get_table(f"{_settings.BQ_DATASET}.{name}")
            result[name]=[( f.name, f.field_type) for f in table.schema]

        except Exception as exc:
            result[name] = {"error":f"BigQuery error {exc}"}

    return result
    

def validate_sql(sql:str)->tuple[bool,str]:
    """Run safety checks on generated sql string before it executes.
    Returns (is_valid,reason). reason is empty when is_valid is true.
    """
    stripped = sql.strip().lower()

    if not (stripped.startswith("select") or stripped.startswith("with")):
        return False, "Only read-only SELECT/WITH queries are allowed."

    if _BLOCKED_KEYWORDS.search(sql):
        return False, "Query contains a disallowed write/DDL keyword."
    
    if _settings.BQ_DATASET.split(".")[-1] not in sql:
        return False, f"Query must reference the {_settings.BQ_DATASET} dataset."
    return True, ""

def execute_sql(sql:str)->dict:
    """Validate and run  a SELECT query agains bigquery
    
    Args:
        sql: A full BigQuery Standard SQL SELECT statement.
    Returns:
        {"rows": [...], "row_count": n} on success, or {"error": "..."} on
        failure. On error, rewrite the query using the error message and
        call this tool again — do not give up after one failure, but do not
        retry more than the configured maximum either.
    """
    ok,reason = validate_sql(sql)

    if not ok:
        return {"error":f"Validation failed: {reason}"}
    
    bounded_sql= sql.rstrip(";")
    if "limit" not in bounded_sql.lower():
        bounded_sql = f"{bounded_sql} LIMIT {_settings.MAX_ROWS_RETURNED}"
    
    client = _get_client()

    try:
        job = client.query(bounded_sql)
        rows = [dict(row) for row in job.result()]
        return {"rows": rows, "row_count": len(rows), "sql_executed": bounded_sql}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    
