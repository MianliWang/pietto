SELECT
    'O''Reilly' AS `QuotedText`,
    '\\''; --' AS `EscapedText`,
    '\b\n\r\t' AS `ControlText`,
    '你好' AS `UnicodeText`,
    NULL AS `Nothing`,
    TRUE AS `Truth`,
    FALSE AS `Falsehood`,
    42 AS `Count`,
    1.5 AS `Ratio`,
    `order` AS `ReservedName`,
    `Rows`.`email` AS `QualifiedEmail`
FROM `Sales.Compat``ibilityRows`
WHERE `email` = '\\''; --'
