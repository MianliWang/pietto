-- FirstRelation
SELECT
    "id" AS "id",
    "email" AS "email"
FROM "public"."users"
WHERE "active" = TRUE;

-- SecondRelation
WITH "FirstRelation" AS (
SELECT
    "id" AS "id",
    "email" AS "email"
FROM "public"."users"
WHERE "active" = TRUE
)
SELECT
    lower(trim("email")) AS "normalized_email"
FROM "FirstRelation";
