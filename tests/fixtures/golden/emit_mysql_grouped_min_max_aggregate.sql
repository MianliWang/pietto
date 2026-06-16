SELECT
    `status` AS `status`,
    MIN(`amount`) AS `smallest_amount`,
    MAX(`created_at`) AS `latest_created_at`
FROM `orders`
WHERE `status` = 'paid'
GROUP BY
    `status`
