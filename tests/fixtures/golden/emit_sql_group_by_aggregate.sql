SELECT
    "status" AS "status",
    COUNT(*) AS "total",
    SUM("amount") AS "revenue"
FROM "orders"
WHERE "status" = 'paid'
GROUP BY
    "status"
