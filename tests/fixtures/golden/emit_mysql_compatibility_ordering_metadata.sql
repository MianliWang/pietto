SELECT
    `id` AS `id`,
    `email` AS `email`
FROM `app.users`
WHERE `active` = TRUE

SELECT
    LOWER(TRIM(`email`)) AS `normalized_email`
FROM `FirstRelation`
