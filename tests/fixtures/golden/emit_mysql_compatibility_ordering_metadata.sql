-- FirstRelation
SELECT
    `id` AS `id`,
    `email` AS `email`
FROM `app`.`users`
WHERE `active` = TRUE;

-- SecondRelation
WITH `FirstRelation` AS (
SELECT
    `id` AS `id`,
    `email` AS `email`
FROM `app`.`users`
WHERE `active` = TRUE
)
SELECT
    LOWER(TRIM(`email`)) AS `normalized_email`
FROM `FirstRelation`;
