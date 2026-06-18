SELECT
    SUM(`amount`) AS `total_amount`,
    SUM(`orders`.`amount`) AS `total_amount_qualified`,
    AVG(`amount`) AS `average_amount`,
    AVG(`orders`.`amount`) AS `average_amount_qualified`,
    MIN(`amount`) AS `smallest_amount`,
    MIN(`orders`.`amount`) AS `smallest_amount_qualified`,
    MAX(`amount`) AS `largest_amount`,
    MAX(`orders`.`amount`) AS `largest_amount_qualified`
FROM `orders` AS `orders`
WHERE `status` = 'paid'
