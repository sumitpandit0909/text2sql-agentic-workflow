# TheLook E-commerce — Table Schema Reference
> **IMPORTANT:** Every SQL query MUST use fully-qualified table names in the exact form `bigquery-public-data.thelook_ecommerce.<table>` (in backticks) — never bare table names like `orders` or `order_items` alone.

Source: `bigquery-public-data.thelook_ecommerce`
Verified via live queries — enum values below are exact, not guessed.

## orders

| Column | Type | Notes |
|---|---|---|
| order_id | INTEGER | Primary key |
| user_id | INTEGER | FK -> users.id |
| status | STRING | Enum: Cancelled, Complete, Processing, Returned, Shipped |
| gender | STRING | Enum: M, F |
| created_at | TIMESTAMP | Order placed |
| shipped_at | TIMESTAMP | Nullable |
| delivered_at | TIMESTAMP | Nullable |
| returned_at | TIMESTAMP | Nullable |
| num_of_item | INTEGER | Item count in this order |

## order_items

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| order_id | INTEGER | FK -> orders.order_id |
| user_id | INTEGER | FK -> users.id |
| product_id | INTEGER | FK -> products.id |
| inventory_item_id | INTEGER | FK -> inventory_items.id |
| status | STRING | Enum: Cancelled, Complete, Processing, Shipped, Returned |
| created_at | TIMESTAMP | |
| shipped_at | TIMESTAMP | Nullable |
| delivered_at | TIMESTAMP | Nullable |
| returned_at | TIMESTAMP | Nullable |
| sale_price | FLOAT | **Use this for revenue calculations** (SUM(sale_price)) |

## users

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| first_name / last_name | STRING | |
| email | STRING | |
| age | INTEGER | |
| gender | STRING | Enum: M, F |
| state / city / country | STRING | |
| street_address / postal_code | STRING | |
| latitude / longitude | FLOAT | |
| traffic_source | STRING | Enum: Organic, Search, Email, Facebook, Display |
| created_at | TIMESTAMP | Signup date — use for "user growth" questions |
| user_geom | GEOGRAPHY | Rarely needed for text-to-SQL |

## products

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| cost | FLOAT | Wholesale cost |
| retail_price | FLOAT | Sale price to customer |
| category | STRING | e.g. "Sneakers", "Jeans" — use for category-based questions |
| department | STRING | e.g. "Men", "Women" |
| name / brand / sku | STRING | |
| distribution_center_id | INTEGER | FK -> distribution_centers.id |

## inventory_items

Denormalized per-unit copy of product info at time of stocking. Use `orders`/`order_items` for sales questions — use this table only for inventory/stock-level questions.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| product_id | INTEGER | FK -> products.id |
| created_at | TIMESTAMP | Stocked date |
| sold_at | TIMESTAMP | **NULL = still in stock**, non-null = sold |
| cost | FLOAT | |
| product_category / product_name / product_brand / product_department / product_sku | STRING | Denormalized copies of products table |
| product_retail_price | FLOAT | |
| product_distribution_center_id | INTEGER | FK -> distribution_centers.id |

## distribution_centers

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| name | STRING | |
| latitude / longitude | FLOAT | |
| distribution_center_geom | GEOGRAPHY | |

## Common query patterns

- **Revenue**: `SUM(sale_price)` from `bigquery-public-data.thelook_ecommerce.order_items`, filtered by `status != 'Cancelled'` for realized revenue.
- **Order volume**: `COUNT(*)` from `bigquery-public-data.thelook_ecommerce.orders`, grouped by `DATE(created_at)`.
- **User growth**: `COUNT(*)` from `bigquery-public-data.thelook_ecommerce.users`, grouped by `DATE(created_at)`.
- **Current inventory level**: `COUNT(*)` from `bigquery-public-data.thelook_ecommerce.inventory_items` WHERE `sold_at IS NULL`.
- **Top products**: join `bigquery-public-data.thelook_ecommerce.order_items` -> `bigquery-public-data.thelook_ecommerce.products` on `product_id`.