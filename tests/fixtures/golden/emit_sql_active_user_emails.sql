-- active_users
SELECT
    "id" AS "id",
    "email" AS "email",
    lower(trim("email")) AS "email_norm"
FROM "public"."users"
WHERE "deleted_at" IS NULL;

-- active_user_emails
WITH "active_users" AS (
SELECT
    "id" AS "id",
    "email" AS "email",
    lower(trim("email")) AS "email_norm"
FROM "public"."users"
WHERE "deleted_at" IS NULL
)
SELECT
    "email" AS "email",
    "email_norm" AS "email_norm"
FROM "active_users";
