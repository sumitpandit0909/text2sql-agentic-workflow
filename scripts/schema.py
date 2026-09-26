from app.tools.bigquery_tool import execute_sql

print("Order statuses:", execute_sql('SELECT DISTINCT status FROM `bigquery-public-data.thelook_ecommerce.orders`'))
print("Order item statuses:", execute_sql('SELECT DISTINCT status FROM `bigquery-public-data.thelook_ecommerce.order_items`'))
print("User genders:", execute_sql('SELECT DISTINCT gender FROM `bigquery-public-data.thelook_ecommerce.users`'))
print("User traffic sources:", execute_sql('SELECT DISTINCT traffic_source FROM `bigquery-public-data.thelook_ecommerce.users`'))
