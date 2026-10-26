-- paid_order_stats
SELECT
    COUNT(*) AS `total`
FROM `orders`
WHERE `status` = 'paid';
