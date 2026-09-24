from google.cloud import bigquery
# from app.core.config import settings

client = bigquery.Client(project="youri-506314")

query= """
SELECT table_name
FROM `bigquery-public-data.thelook_ecommerce.INFORMATION_SCHEMA.TABLES`
"""

for row in client.query(query).result():
    print(row.table_name)