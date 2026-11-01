-- revenue_by_status
SELECT
    "status" AS "status",
    COUNT(*) AS "total",
    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) AS "revenue"
FROM "orders"
WHERE "status" = 'paid'
GROUP BY
    "status";
