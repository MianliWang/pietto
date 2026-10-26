-- paid_order_stats
SELECT
    COUNT(*) AS "total",
    SUM("amount") AS "revenue",
    SUM("score") AS "score_total",
    AVG(CAST("amount" AS double precision)) AS "average_amount",
    AVG("score") AS "average_score"
FROM "orders"
WHERE "status" = 'paid';
