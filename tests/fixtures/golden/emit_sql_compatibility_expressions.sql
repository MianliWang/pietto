SELECT
    lower(trim("email")) AS "normalized",
    length("email") AS "text_length",
    "score" = 10 AS "equal",
    "score" <> 11 AS "not_equal",
    "score" < 12 AS "less",
    "score" <= 13 AS "less_equal",
    "score" > 8 AS "greater",
    "score" >= 7 AS "greater_equal",
    "score" BETWEEN 1 AND 100 AS "ranged",
    "email" IS NOT NULL AS "not_null",
    +"score" AS "positive",
    -"score" AS "negative",
    "score" + 2 AS "added",
    "score" - 2 AS "subtracted",
    "score" * 2 AS "multiplied",
    "score" / 2 AS "divided",
    "score" % 2 AS "modulo",
    "active" AND TRUE AS "conjunction",
    "active" OR FALSE AS "disjunction",
    "score" + (2 * 3) AS "precedence",
    ("score" + 2) * 3 AS "grouped"
FROM "analytics.metrics"
WHERE (("age" >= 18) AND ("deleted_at" IS NULL)) OR ("email" ~ '.+@.+')
