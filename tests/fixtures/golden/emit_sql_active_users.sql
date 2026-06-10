SELECT
    "id" AS "id",
    "email" AS "email",
    lower(trim("email")) AS "email_norm"
FROM "public.users"
WHERE "deleted_at" IS NULL
