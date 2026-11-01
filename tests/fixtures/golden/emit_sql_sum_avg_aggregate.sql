-- paid_order_stats
SELECT
    COUNT(*) AS "total",
    CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8) AS "revenue",
    SUM("score") AS "score_total",
    AVG(CAST("amount" AS double precision)) AS "average_amount",
    AVG("score") AS "average_score"
FROM "orders"
WHERE "status" = 'paid';
