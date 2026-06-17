SELECT
    COUNT(*) AS "total",
    COUNT("amount") AS "known_amounts",
    COUNT("orders"."score") AS "known_scores"
FROM "orders" AS "orders"
WHERE "status" = 'paid'
