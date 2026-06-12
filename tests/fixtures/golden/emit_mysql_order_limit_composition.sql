SELECT
    `id` AS `id`,
    LOWER(`email`) AS `normalized`
FROM `users`
WHERE `active` = TRUE
ORDER BY
    `created_at` DESC,
    `id` ASC
LIMIT 100
