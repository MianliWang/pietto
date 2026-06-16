SELECT
    COUNT(*) AS "total",
    SUM("amount") AS "revenue",
    SUM("score") AS "score_total",
    AVG("amount") AS "average_amount",
    AVG("score") AS "average_score"
FROM "orders"
WHERE "status" = 'paid'
