from google.cloud import bigquery

def main():
    print("Testing BigQuery connection...")
    client = bigquery.Client(project="youri-506314")
    query = """
        SELECT status, count(1) AS total_orders
        FROM `bigquery-public-data.thelook_ecommerce.orders`
        GROUP BY status
        ORDER BY total_orders DESC
        LIMIT 5
    """
    job = client.query(query)
    results = job.result()
    print("Connection successful! Sample query results from thelook_ecommerce:")
    for row in results:
        print(f"  - Status: {row.status:<12} Total Orders: {row.total_orders}")

if __name__ == "__main__":
    main()
