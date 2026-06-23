---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-23
---

# Building SQL Queries from the `schema` Ontology

> **Status: non-normative guide.** This document is explanatory implementation
> guidance complementing [`../SPEC.md`](../SPEC.md). It is not part of the
> behavior contract; where it differs from the SPEC or
> [`../schemas/`](../schemas/), those win. The Python snippet below is
> **illustrative** — a readable reference to copy and adapt, **not** a
> maintained module shipped with this repo.

You have a SQL warehouse — fact and dimension tables, foreign keys, indexes —
and you want an agent to get fast, precise, cited answers out of it. This guide
shows how to put that warehouse *behind* MCP-A so the client only ever sees the
seven primitives ([`surfacing-apis.md`](./surfacing-apis.md)): the client calls
`query`; the server builds and runs SQL.

A `query` with `response_schema` set asks the server for typed values. To get
them from a SQL backend, the server builds a `SELECT` statement **dynamically**
from two inputs:

1. The domain's **ontology** — exactly what the `schema` primitive returns
   ([`../schemas/schema.response.json`](../schemas/schema.response.json)):
   entities, fields (with `type`, `unit`, `nullable`, `allowed_aggregations`,
   `enum_values`), and relationships (with `cardinality`).
2. A **parsed intent** — the structured query plan produced by the server-side
   query-building model (target entity, requested fields, filters, group-by,
   aggregations). See
   [`intent-and-query-building.md`](./intent-and-query-building.md), template B,
   for how that plan is produced.

SQL is the **canonical deterministic-aggregation backend.** Where REST has to
fetch rows and reduce them in application code
([`rest-api-mapping.md`](./rest-api-mapping.md)), SQL computes rollups *in the
database* with aggregate functions and `GROUP BY`. This is exactly what
[`../SPEC.md`](../SPEC.md#aggregation-correctness-conformance) (Aggregation
Correctness Conformance) and [`../CONFORMANCE.md`](../CONFORMANCE.md) require:

> All advertised aggregations MUST be computed deterministically server-side via
> database queries, GraphQL resolvers, or direct computation over source data
> (not via learned model inference).

"Database queries" is the SQL case, and a SQL warehouse satisfies it most
naturally of the three backends — `SUM`, `AVG`, `MIN`, `MAX`, `COUNT` over
`GROUP BY` are the database's job. The ontology is still the **guardrail**: the
builder may only emit aggregate functions the ontology declares, which is why an
aggregation the ontology omits must fail with `AGGREGATION_NOT_ALLOWED` rather
than be guessed.

## Mapping tables: ontology → SQL

These are *conventions*; your warehouse's actual table and column names are up to
you, but a consistent mapping keeps the builder simple and the identifier
allow-list (below) easy to derive.

### Entity → table

| Ontology `Entity.type` | SQL |
|------------------------|-----|
| `FactSales` | table `fact_sales` (aliased `f`) |
| `DimProduct` | table `dim_product` (aliased `p`) |
| `DimDate` | table `dim_date` (aliased `d`) |

Convention: PascalCase entity type → `snake_case` table name.

### Field → column

| Ontology `Field.type` | SQL column |
|-----------------------|------------|
| `scalar` (no `unit`) | a column of the natural SQL type |
| `scalar` with `unit: "USD"` / `"count"` | a numeric column (`NUMERIC`/`INT`) |
| `enum` (+`enum_values`) | a column constrained to the enum values; a `GROUP BY` / `WHERE` key |
| `date` | a `DATE`/`TIMESTAMP` column; range-filterable and `ORDER BY`-able |
| `reference` | a primary key or foreign-key column (`sale_id`, `product_id`) |

Convention: ontology field name → same `snake_case` column name.

### Relationship (cardinality) → JOIN

| `Relationship.cardinality` | SQL |
|----------------------------|-----|
| `one-to-one` | `JOIN dim_x ON f.x_id = x.x_id` (one matching row, e.g. a fact→dimension FK) |
| `one-to-many` | `JOIN` from the parent's key to the child's FK (fan-out; group/aggregate to collapse) |
| `many-to-many` | two `JOIN`s through the bridge table |

The relationship's `target_entity` names the table to join; the `reference`
fields on each side name the join columns.

### `allowed_aggregations` → SQL aggregate functions + GROUP BY

| Ontology aggregation | SQL |
|----------------------|-----|
| `sum` | `SUM(<col>)` |
| `avg` | `AVG(<col>)` |
| `min` / `max` | `MIN(<col>)` / `MAX(<col>)` |
| `count` | `COUNT(<col>)` (record count: `COUNT(<identity_col>)`) |
| group-by | `GROUP BY <dimension cols>` |

**Hard rule (same as every backend):** a plain record count — `COUNT` over the
entity's identity (a `reference` field) — is always available and needs no
`allowed_aggregations` entry. For every **value aggregation** (`sum`/`avg`/`min`/
`max`, and `count` on a dimension/enum field), only emit the aggregate function
if that aggregation is in the field's `allowed_aggregations`. Anything else is a
builder error that must surface as `AGGREGATION_NOT_ALLOWED`
([`../SPEC.md`](../SPEC.md#error-model)), exactly as
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json)
does for the sales domain.

### SQL-injection safety

The builder constructs SQL from a model-produced intent, so it MUST be safe by
construction:

- **Parameterize all values.** Filter values and literals go in bound parameters
  (`WHERE d.quarter = $1`), never string-interpolated into the SQL text.
- **Allow-list all identifiers.** Table and column names come *only* from the
  ontology. Map each ontology entity/field to its SQL identifier through a lookup
  derived from the `schema` response; reject any identifier not in that map.
  Never pass a model-produced string straight into a table/column position.

## The dynamic algorithm

Given `ontology` (a `schema` response) and `intent` (a parsed query plan):

1. **Resolve the table from intent.** Look up `intent.entity` in
   `ontology.entities`; map it to its table + alias. If absent → error.
2. **SELECT columns.** For each name in `intent.fields`, confirm it exists on
   the entity and map it to its column. (For a pure rollup, the only selected
   non-aggregate columns are the group-by dimensions.)
3. **JOIN per relationships/intent.** For each requested relationship (or each
   group-by/filter that lives on a related entity), look it up in the entity's
   `relationships`, resolve the target table, and emit a `JOIN` on the two
   `reference` columns.
4. **WHERE filters.** Translate `intent.filters` into a `WHERE` clause of
   parameterized predicates, validating enum filter values against `enum_values`.
5. **Apply ONLY allowed aggregations.** For each `(field, op)` in
   `intent.aggregations`: a plain **record count** — `COUNT` over the entity's
   identity (a `reference` field) — is always permitted and is *not* gated by
   `allowed_aggregations`. Every other combination is a **value aggregation** and
   must satisfy `op ∈ field.allowed_aggregations`; if not → raise
   `AGGREGATION_NOT_ALLOWED` with the offending field, op, and the allowed set;
   **do not** silently drop or substitute. Emit the aggregate function, and add a
   `GROUP BY` over the `intent.group_by` dimension columns.
6. **ORDER / LIMIT.** Apply any ordering (often by a computed aggregate) and a
   `LIMIT` to bound the result set.
7. **Emit parameterized SQL.** Render the `SELECT`, `JOIN`s, `WHERE`, `GROUP BY`,
   `ORDER BY`, and `LIMIT` into a single statement with bound parameters and
   allow-listed identifiers (never string-interpolated values).

## Illustrative Python builder

> **Illustrative only.** This is a teaching reference, not a tracked module in
> this repo, and is intentionally not linted or tested by CI. Adapt it to your
> SQL dialect, identifier-quoting, and parameter style.

```python
"""Build a parameterized SQL statement from an MCP-A `schema` ontology + intent.

Why: shows how structured-mode `query` turns the ontology guardrail into a
concrete SQL statement, applying ONLY allowed_aggregations as SQL aggregate
functions so structured answers stay precise-by-construction and deterministic
(SPEC §Aggregation Correctness), with values bound (not interpolated) and
identifiers allow-listed from the ontology (injection safety).
What: pure function (ontology dict, intent dict) -> (sql_text, params list).
Test: feed the warehouse ontology (examples/24-schema-sql.response.json) and a
revenue-by-category intent; assert the SQL contains SUM(f.revenue),
COUNT(f.sale_id), GROUP BY p.category and that filter values appear in params,
not in the SQL text; assert AVG on an enum (e.g. ["category","avg"]) raises
AggregationNotAllowed.
"""
from __future__ import annotations


class AggregationNotAllowed(Exception):
    """Raised when an intent requests an aggregation the ontology forbids.

    Why: maps directly to the AGGREGATION_NOT_ALLOWED abstract error code; the
    builder must fail loudly instead of guessing (SPEC §Error Model).
    What: carries the offending field, the requested op, and the allowed set.
    Test: request `avg` on a field whose allowed_aggregations omits it; assert raised.
    """

    def __init__(self, field: str, op: str, allowed: list[str]) -> None:
        super().__init__(f"{op} not allowed on {field}; allowed: {allowed}")
        self.field = field
        self.op = op
        self.allowed = allowed


def _table(entity_type: str) -> str:
    """Why: map an ontology entity to its SQL table name (allow-list source).
    What: 'FactSales' -> 'fact_sales' (PascalCase -> snake_case).
    Test: assert _table('DimProduct') == 'dim_product'.
    """
    out = [entity_type[0].lower()]
    for ch in entity_type[1:]:
        out.append("_" + ch.lower() if ch.isupper() else ch)
    return "".join(out)


def _index_fields(entity: dict) -> dict[str, dict]:
    """Why: O(1) lookup of a field's metadata (type, allowed_aggregations).
    What: returns {field_name: field_obj} for one entity.
    Test: index the FactSales entity; assert 'revenue' in the result.
    """
    return {f["name"]: f for f in entity["fields"]}


def build_sql(ontology: dict, intent: dict) -> tuple[str, list]:
    """Why: the core of structured-mode SQL construction.
    What: renders a parameterized SELECT from the ontology + parsed intent.
    Test: see module docstring — revenue-by-category over the warehouse ontology.
    """
    # 1. Resolve the table from intent (identifiers are allow-listed via ontology).
    entities = {e["type"]: e for e in ontology["entities"]}
    if intent["entity"] not in entities:
        raise ValueError(f"unknown entity: {intent['entity']}")
    entity = entities[intent["entity"]]
    fields = _index_fields(entity)
    table = _table(intent["entity"])
    alias = "f"

    select_parts: list[str] = []
    group_by: list[str] = []

    # 2. SELECT group-by dimension columns (allow-listed from the ontology).
    for g in intent.get("group_by", []):
        if g not in fields:
            raise ValueError(f"unknown group_by field: {g}")
        select_parts.append(f"{alias}.{g}")
        group_by.append(f"{alias}.{g}")

    # 5. Apply ONLY allowed aggregations (the precision guardrail).
    for field_name, op in intent.get("aggregations", []):
        meta = fields.get(field_name)
        if meta is None:
            raise ValueError(f"unknown aggregation field: {field_name}")
        # Record-count convention: COUNT over the entity's identity (a `reference`
        # field) is ALWAYS available and is NOT gated by allowed_aggregations.
        # Only VALUE aggregations (sum/avg/min/max, count on dimension/enum
        # fields) must appear in allowed_aggregations.
        is_record_count = op == "count" and meta.get("type") == "reference"
        allowed = meta.get("allowed_aggregations", [])
        if not is_record_count and op not in allowed:
            raise AggregationNotAllowed(field_name, op, allowed)
        fn = op.upper()  # sum -> SUM, count -> COUNT, ...
        select_parts.append(f"{fn}({alias}.{field_name}) AS {op}_{field_name}")

    # 4. WHERE filters — values BOUND as params, never interpolated.
    where_parts: list[str] = []
    params: list = []
    for key, value in intent.get("filters", {}).items():
        if key not in fields:
            raise ValueError(f"unknown filter field: {key}")
        if isinstance(value, list):
            placeholders = ", ".join(f"${len(params) + i + 1}" for i in range(len(value)))
            where_parts.append(f"{alias}.{key} IN ({placeholders})")
            params.extend(value)
        else:
            params.append(value)
            where_parts.append(f"{alias}.{key} = ${len(params)}")

    # 7. Emit parameterized SQL.
    sql = f"SELECT {', '.join(select_parts) or f'{alias}.*'} FROM {table} {alias}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_by:
        sql += " GROUP BY " + ", ".join(group_by)
    return sql + ";", params
```

## Worked example: revenue by product category

Take the ontology from
[`../examples/24-schema-sql.response.json`](../examples/24-schema-sql.response.json)
and the intent parsed from the structured `query` in
[`../examples/25-query-sql.request.json`](../examples/25-query-sql.request.json)
(*"What was total revenue, total units, and number of sales by product category
last quarter?"*):

```python
intent = {
    "entity": "FactSales",
    "fields": [],
    "filters": {"quarter": "Q1", "year": 2026},
    "group_by": ["category"],
    "aggregations": [("revenue", "sum"), ("units", "sum"), ("sale_id", "count")],
}
```

`FactSales.revenue` and `FactSales.units` both declare
`allowed_aggregations: ["sum","avg","min","max","count"]`, so their `sum` is an
allowed value aggregation. `FactSales.sale_id` is a `reference` field with no
`allowed_aggregations`, but `("sale_id", "count")` is a record count over the
entity's identity — always permitted and not gated — so all three pass the step-5
guardrail. With `category` (on `DimProduct`) and `quarter`/`year` (on `DimDate`)
the builder joins both dimensions; the emitted SQL is the parameterized statement
recorded as the citation snippet in
[`../examples/25-query-sql.response.json`](../examples/25-query-sql.response.json):

```sql
SELECT p.category,
       SUM(f.revenue)   AS total_revenue,
       SUM(f.units)     AS total_units,
       COUNT(f.sale_id) AS sale_count
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
JOIN dim_date    d ON f.date_id    = d.date_id
WHERE d.quarter = $1 AND d.year = $2
GROUP BY p.category
ORDER BY total_revenue DESC;   -- params: ['Q1', 2026]
```

The database computes `SUM`/`SUM`/`COUNT` per category — deterministic,
server-side, with the quarter filter **bound** as parameters, not interpolated.
The server maps each returned row back to a typed object in the `query`
response's `structured` array:

```json
"structured": [
  { "category": "electronics", "total_revenue": 4820150, "total_units": 18204, "sale_count": 9912, "currency": "USD" }
]
```

and records the generated SQL as a citation snippet under
`source_system: "warehouse-sql"`, alongside a `routing_decision`.

**Now the failure case.** If the intent had asked for `("category", "avg")` —
averaging an enum — step 5 finds `avg ∉ DimProduct.category.allowed_aggregations`
(which is `["count"]`) and raises `AggregationNotAllowed`. The server returns
`AGGREGATION_NOT_ALLOWED` per [`../SPEC.md`](../SPEC.md#error-model), mirroring
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json).
It does not run a meaningless query.

## The precision pillar

Aggregations in MCP-A are **computed, not estimated**, and SQL is the backend
where that is most direct: the `SELECT ... GROUP BY` does the math in the
database. The builder's only job is to ensure it asks for *only* the aggregations
the ontology promised (step 5) and to keep the statement injection-safe (bound
values + allow-listed identifiers). Writes to a SQL-backed domain map to the
`action` primitive ([`../SPEC.md`](../SPEC.md#7-action)) — an `INSERT`/`UPDATE`/
`DELETE` recorded as an `ActionEffect` — exactly as the REST guide describes for
its mutations.

## See also

- [`surfacing-apis.md`](./surfacing-apis.md) — where this builder fits in the end-to-end flow (step 3.2).
- [`rest-api-mapping.md`](./rest-api-mapping.md) — the REST backend, where aggregation is fetch-and-reduce.
- [`graphql-query-builder.md`](./graphql-query-builder.md) — the GraphQL backend builder this mirrors.
- [`intent-and-query-building.md`](./intent-and-query-building.md) — how the `intent` dict is produced.
- [`../schemas/schema.response.json`](../schemas/schema.response.json) — the ontology contract this consumes.
