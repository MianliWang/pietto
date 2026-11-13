-- LiteralCompatibility
SELECT
    'O''Reilly' AS `QuotedText`,
    _utf8mb4 X'5c273b202d2d' AS `EscapedText`,
    _utf8mb4 X'080a0d09' AS `ControlText`,
    '你好' AS `UnicodeText`,
    NULL AS `Nothing`,
    TRUE AS `Truth`,
    FALSE AS `Falsehood`,
    42 AS `Count`,
    1.5 AS `Ratio`,
    `order` AS `ReservedName`,
    `Rows`.`email` AS `QualifiedEmail`
FROM `Sales`.`Compat``ibilityRows` AS `Rows`
WHERE `email` = _utf8mb4 X'5c273b202d2d';
