SELECT
    `status` AS `status`,
    COUNT(DISTINCT `customer_id`) AS `unique_customers`,
    COUNT(DISTINCT `orders`.`status`) AS `unique_statuses`
FROM `orders` AS `orders`
WHERE `status` = 'paid'
GROUP BY
    `status`
