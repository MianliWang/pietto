-- active_accounts
SELECT
    `accounts`.`id` AS `id`,
    `accounts`.`name` AS `label`,
    `accounts`.`score` AS `score`
FROM `accounts`
WHERE `accounts`.`active` AND (`accounts`.`score` IS NOT NULL);

-- ranked_names
SELECT
    `accounts`.`id` AS `id`,
    `accounts`.`name` AS `name`,
    `accounts`.`active` = FALSE AS `flagged`,
    'account' AS `kind`,
    1.5 AS `weight`,
    9223372036854775807 AS `rank`
FROM `accounts`
WHERE ((`accounts`.`name` >= 'M') OR (`accounts`.`name` = 'O''Neil `é`')) AND (NOT (`accounts`.`score` < 0.5))
ORDER BY
    `accounts`.`score` DESC NULLS FIRST,
    `accounts`.`name` ASC NULLS LAST,
    `accounts`.`id` ASC NULLS LAST
LIMIT 20;

-- region_counts
SELECT
    `accounts`.`region` AS `region`,
    COUNT(*) AS `accounts`,
    COUNT(`accounts`.`score`) AS `scored`,
    MIN(`accounts`.`id`) AS `low`,
    MAX(`accounts`.`score`) AS `high`
FROM `accounts`
WHERE `accounts`.`region` IS NOT NULL
GROUP BY
    `accounts`.`region`
ORDER BY
    COUNT(*) DESC NULLS FIRST,
    `accounts`.`region` ASC NULLS LAST;

-- totals
SELECT
    COUNT(*) AS `rows`,
    MAX(`accounts`.`id`) AS `top`
FROM `accounts`;
