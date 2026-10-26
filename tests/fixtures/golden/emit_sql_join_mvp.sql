-- order_names
SELECT
    "orders"."id" AS "order_id",
    "customer"."name" AS "customer_name"
FROM "shop"."orders" AS "orders"
INNER JOIN "shop"."customers" AS "customer" ON "orders"."customer_id" = "customer"."id";

-- customer_regions
SELECT
    "customers"."id" AS "customer_id",
    "region"."label" AS "region_label"
FROM "shop"."customers" AS "customers"
LEFT JOIN "shop"."regions" AS "region" ON "customers"."region_id" = "region"."id";

-- orders_or_customers
SELECT
    "orders"."id" AS "order_id",
    "customer"."name" AS "customer_name"
FROM "shop"."orders" AS "orders"
RIGHT JOIN "shop"."customers" AS "customer" ON "orders"."customer_id" = "customer"."id";

-- order_customer_pairs
SELECT
    "orders"."id" AS "order_id",
    "customer"."id" AS "customer_id"
FROM "shop"."orders" AS "orders"
FULL JOIN "shop"."customers" AS "customer" ON "orders"."customer_id" = "customer"."id";

-- order_region_pairs
SELECT
    "orders"."id" AS "order_id",
    "region"."label" AS "region_label"
FROM "shop"."orders" AS "orders"
CROSS JOIN "shop"."regions" AS "region";

-- customers_with_orders
SELECT
    "id" AS "id",
    "name" AS "name"
FROM "shop"."customers" AS "customers"
WHERE EXISTS (SELECT 1 FROM "shop"."orders" AS "_pietto_value_1" WHERE "customers"."id" = "_pietto_value_1"."customer_id");

-- customers_without_big_orders
SELECT
    "customers"."id" AS "customer_id"
FROM "shop"."customers" AS "customers"
WHERE NOT EXISTS (SELECT 1 FROM "shop"."orders" AS "_pietto_value_2" WHERE ("customers"."id" = "_pietto_value_2"."customer_id") AND ("_pietto_value_2"."amount" > 100));

-- big_order_names
SELECT
    "orders"."id" AS "order_id",
    "customer"."name" AS "customer_name"
FROM "shop"."orders" AS "orders"
INNER JOIN "shop"."customers" AS "customer" ON ("orders"."customer_id" = "customer"."id") AND ("orders"."amount" > 5);

-- orders_with_named_customers
SELECT
    "orders"."id" AS "order_id",
    "customer"."name" AS "customer_name"
FROM "shop"."orders" AS "orders"
LEFT JOIN "shop"."customers" AS "customer" ON ("orders"."customer_id" = "customer"."id") AND ("customer"."name" <> 'x');

-- recent_order_regions
SELECT
    "orders"."id" AS "order_id",
    "customer"."name" AS "customer_name",
    "region"."label" AS "region_label"
FROM "shop"."orders" AS "orders"
INNER JOIN "shop"."customers" AS "customer" ON "orders"."customer_id" = "customer"."id"
LEFT JOIN "shop"."regions" AS "region" ON "customer"."region_id" = "region"."id"
WHERE "orders"."amount" > 1
ORDER BY
    "orders"."id" DESC
LIMIT 10;

-- regions_and_ordering_customers
SELECT
    "region"."label" AS "region_label",
    "customers"."id" AS "customer_id"
FROM "shop"."customers" AS "customers"
RIGHT JOIN "shop"."regions" AS "region" ON ("customers"."region_id" = "region"."id") AND (EXISTS (SELECT 1 FROM "shop"."orders" AS "_pietto_any_1" WHERE "customers"."id" = "_pietto_any_1"."customer_id"));

-- customer_peers
SELECT
    "customers"."id" AS "customer_id",
    "peer"."id" AS "peer_id"
FROM "shop"."customers" AS "customers"
LEFT JOIN "shop"."customers" AS "peer" ON ("peer"."region_id" = "customers"."region_id") AND ("peer"."id" <> "customers"."id");

-- named_customers
SELECT
    "id" AS "id",
    "name" AS "name"
FROM "shop"."customers"
WHERE "name" <> '';

-- orders_of_named_customers
WITH "named_customers" AS (
SELECT
    "id" AS "id",
    "name" AS "name"
FROM "shop"."customers"
WHERE "name" <> ''
)
SELECT
    "orders"."id" AS "order_id",
    "c"."name" AS "customer_name"
FROM "shop"."orders" AS "orders"
INNER JOIN "named_customers" AS "c" ON "orders"."customer_id" = "c"."id";

-- order_stats
SELECT
    "customer"."name" AS "name",
    MAX("orders"."amount") AS "biggest",
    COUNT(*) AS "n"
FROM "shop"."orders" AS "orders"
INNER JOIN "shop"."customers" AS "customer" ON "orders"."customer_id" = "customer"."id"
GROUP BY
    "customer"."id",
    "customer"."name"
HAVING
    COUNT(*) > 1;
