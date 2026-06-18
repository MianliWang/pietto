SELECT
    `status` AS `status`,
    SUM(`amount`) AS `total_amount`,
    AVG(`amount`) AS `average_amount`,
    MIN(`amount`) AS `smallest_amount`,
    MAX(`orders`.`amount`) AS `largest_amount`
FROM `orders` AS `orders`
WHERE `status` = 'paid'
GROUP BY
    `status`
