SELECT
    MIN("amount") AS "smallest_amount",
    MAX("score") AS "highest_score",
    MIN("orders"."order_date") AS "first_order_date",
    MAX("orders"."created_at") AS "latest_created_at"
FROM "orders" AS "orders"
WHERE "status" = 'paid'
