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

1. **Build the table + alias map.** Look up `intent.entity` (the primary fact)
   in `ontology.entities`; if absent → error. Map it *and* each dimension it
   relates to (via `relationships`) to a table name + a short unique alias
   (e.g. `FactSales`→`fact_sales f`, `DimProduct`→`dim_product p`,
   `DimDate`→`dim_date d`). Also build a field→owning-entity index by searching
   the primary entity's fields first, then each related dimension's fields, so a
   column like `category` resolves to `DimProduct` and `quarter`/`year` to
   `DimDate`.
2. **SELECT columns, qualified by owner.** For each name in `intent.fields` and
   each group-by dimension, resolve it through the field→owner index and qualify
   it with its owning entity's alias (`category`→`p.category`). (For a pure
   rollup, the only selected non-aggregate columns are the group-by dimensions.)
3. **JOIN every referenced dimension.** Whenever a selected field, group-by, or
   filter resolves to a dimension other than the primary fact, that dimension
   must be JOINed. The dimension's identity (its first `reference` field, e.g.
   `product_id`) names *both* the foreign key on the fact table and the primary
   key on the dimension, so emit `JOIN dim_x x ON f.x_id = x.x_id`.
4. **WHERE filters.** Translate `intent.filters` into a `WHERE` clause of
   parameterized predicates, validating enum filter values against `enum_values`.
5. **Apply ONLY allowed aggregations.** For each `(field, op, alias)` in
   `intent.aggregations`: a plain **record count** — `COUNT` over the entity's
   identity (a `reference` field) — is always permitted and is *not* gated by
   `allowed_aggregations`. Every other combination is a **value aggregation** and
   must satisfy `op ∈ field.allowed_aggregations`; if not → raise
   `AGGREGATION_NOT_ALLOWED` with the offending field, op, and the allowed set;
   **do not** silently drop or substitute. Emit the aggregate function over the
   owner-qualified column, labelled with the plan's output `alias` (e.g.
   `SUM(f.revenue) AS total_revenue`), and add a `GROUP BY` over the
   `intent.group_by` dimension columns.
6. **ORDER / LIMIT.** Apply any ordering (often by a computed aggregate),
   validating the direction against `{ASC, DESC}` and the order-by column against
   the output aliases the builder produced; optionally bound the result with a
   `LIMIT` when the intent supplies one.
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
COUNT(f.sale_id), the JOINs to dim_product/dim_date, GROUP BY p.category, and
that filter values appear in params, not in the SQL text; assert AVG on an enum
(e.g. ("category","avg",...)) raises AggregationNotAllowed.
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


def _identity(entity: dict) -> str:
    """Why: JOINs need each table's key column; by convention the entity's
    first `reference` field is its identity (primary key), and the fact table
    carries the same-named column as the foreign key.
    What: returns the first `reference` field name (e.g. DimProduct -> 'product_id').
    Test: assert _identity(dim_product_entity) == 'product_id'.
    """
    for f in entity["fields"]:
        if f["type"] == "reference":
            return f["name"]
    raise ValueError(f"entity {entity['type']} has no reference identity field")


def _alias(table: str, taken: set[str]) -> str:
    """Why: every column is qualified by its owning table's alias, so each
    table needs a short, unique alias derived deterministically from the ontology.
    What: fact tables alias to the first word's initial (fact_sales -> f);
    dimensions alias to the distinctive last word's initial (dim_product -> p,
    dim_date -> d), with a numeric suffix on collision.
    Test: _alias('fact_sales', set()) == 'f'; _alias('dim_product', {'f'}) == 'p'.
    """
    words = table.split("_")
    base = words[0][0] if words[0] == "fact" else words[-1][0]
    alias, i = base, 1
    while alias in taken:
        i += 1
        alias = f"{base}{i}"
    return alias


def build_sql(ontology: dict, intent: dict) -> tuple[str, list]:
    """Why: the core of structured-mode SQL construction.
    What: renders a parameterized SELECT from the ontology + parsed intent,
    joining any dimension that a selected field / group-by / filter lives on.
    Test: see module docstring — revenue-by-category over the warehouse ontology.
    """
    # 1. Resolve the primary table, plus a table+alias for each dimension the
    #    primary entity relates to (identifiers are allow-listed via ontology).
    entities = {e["type"]: e for e in ontology["entities"]}
    if intent["entity"] not in entities:
        raise ValueError(f"unknown entity: {intent['entity']}")
    primary = entities[intent["entity"]]

    tables: dict[str, str] = {}   # entity_type -> table name
    aliases: dict[str, str] = {}  # entity_type -> table alias

    def _register(entity_type: str) -> None:
        table = _table(entity_type)
        tables[entity_type] = table
        aliases[entity_type] = _alias(table, set(aliases.values()))

    _register(primary["type"])
    related = {r["target_entity"]: r for r in primary.get("relationships", [])}
    for target in related:
        if target in entities:
            _register(target)
    primary_alias = aliases[primary["type"]]

    # Resolve every field to its OWNING entity: search the primary entity's
    # fields first, then each related dimension's fields.
    owner: dict[str, str] = {}      # field_name -> owning entity_type
    field_meta: dict[str, dict] = {}
    for f in primary["fields"]:
        owner.setdefault(f["name"], primary["type"])
        field_meta.setdefault(f["name"], f)
    for target in related:
        if target not in entities:
            continue
        for f in entities[target]["fields"]:
            owner.setdefault(f["name"], target)
            field_meta.setdefault(f["name"], f)

    used_dims: set[str] = set()

    def _qualify(field_name: str) -> str:
        if field_name not in owner:
            raise ValueError(f"unknown field: {field_name}")
        owning = owner[field_name]
        if owning != primary["type"]:
            used_dims.add(owning)  # this dimension must be JOINed
        return f"{aliases[owning]}.{field_name}"

    select_parts: list[str] = []
    group_by: list[str] = []
    output_aliases: set[str] = set()  # ORDER BY allow-list: aggregation aliases + group-by cols

    # 2. SELECT group-by dimension columns, qualified by their owning table.
    for g in intent.get("group_by", []):
        select_parts.append(_qualify(g))
        group_by.append(_qualify(g))
        output_aliases.add(g)

    # 5. Apply ONLY allowed aggregations (the precision guardrail).
    for field_name, op, out_alias in intent.get("aggregations", []):
        meta = field_meta.get(field_name)
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
        select_parts.append(f"{fn}({_qualify(field_name)}) AS {out_alias}")
        output_aliases.add(out_alias)

    # 4. WHERE filters — values BOUND as params, never interpolated.
    where_parts: list[str] = []
    params: list = []
    for key, value in intent.get("filters", {}).items():
        col = _qualify(key)
        if isinstance(value, list):
            placeholders = ", ".join(f"${len(params) + i + 1}" for i in range(len(value)))
            where_parts.append(f"{col} IN ({placeholders})")
            params.extend(value)
        else:
            params.append(value)
            where_parts.append(f"{col} = ${len(params)}")

    # 3. JOIN each referenced dimension on FK = PK. The dimension's identity
    #    (its first `reference` field, e.g. product_id) names BOTH the foreign
    #    key on the fact table and the primary key on the dimension.
    join_parts: list[str] = []
    for target in related:  # preserves the ontology's relationship order
        if target not in used_dims:
            continue
        key = _identity(entities[target])
        join_parts.append(
            f"JOIN {tables[target]} {aliases[target]} "
            f"ON {primary_alias}.{key} = {aliases[target]}.{key}"
        )

    # 7. Emit parameterized SQL.
    sql = (
        f"SELECT {', '.join(select_parts) or f'{primary_alias}.*'} "
        f"FROM {tables[primary['type']]} {primary_alias}"
    )
    for j in join_parts:
        sql += " " + j
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_by:
        sql += " GROUP BY " + ", ".join(group_by)
    if intent.get("order_by"):  # 6. optional ORDER BY (often a computed alias)
        col, direction = intent["order_by"]
        # Allow-list direction and column so a model-produced order_by cannot
        # inject SQL — same stance as the value-binding/identifier rules above.
        direction = (direction or "DESC").upper()
        if direction not in ("ASC", "DESC"):
            raise ValueError(f"invalid order direction: {direction!r} (expected ASC or DESC)")
        if col not in output_aliases:
            raise ValueError(f"order_by column {col!r} is not a selected output alias")
        sql += f" ORDER BY {col} {direction}"
    if "limit" in intent and intent["limit"] is not None:  # 6. optional LIMIT
        limit = intent["limit"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError(f"limit must be a non-negative int, got {limit!r}")
        sql += f" LIMIT {limit}"
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
    # each aggregation carries (field, op, output-alias)
    "aggregations": [
        ("revenue", "sum", "total_revenue"),
        ("units", "sum", "total_units"),
        ("sale_id", "count", "sale_count"),
    ],
    "order_by": ("total_revenue", "DESC"),
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
