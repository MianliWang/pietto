SELECT
    'O''Reilly' AS "QuotedText",
    E'\\''; --' AS "EscapedText",
    TRUE AS "Truth",
    42 AS "Count",
    1.5 AS "Ratio",
    "order" AS "ReservedName"
FROM "Sales.CompatibilityRows"
WHERE "email" = E'\\''; --'
