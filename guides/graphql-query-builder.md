---
Status: DRAFT
Version: 1.1.0-beta
Date: 2026-07-01
---

# Building GraphQL Queries from the `schema` Ontology

> **Status: non-normative guide.** This document is explanatory implementation
> guidance complementing [`../SPEC.md`](../SPEC.md). It is not part of the
> behavior contract; where it differs from the SPEC or
> [`../schemas/`](../schemas/), those win. The Python snippet below is
> **illustrative** — a readable reference to copy and adapt, **not** a
> maintained module shipped with this repo.

A `query` with `response_schema` set asks the server for typed values. To get
them from a GraphQL backend, the server builds a GraphQL document **dynamically**
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

The ontology is the **guardrail**: the builder may only emit fields and
aggregations the ontology declares. This is what makes structured answers
*precise by construction* — and it is why an aggregation the ontology omits must
fail with `AGGREGATION_NOT_ALLOWED` rather than be guessed.

## Mapping tables: ontology → GraphQL

The ontology vocabulary (defined in
[`../schemas/schema.response.json`](../schemas/schema.response.json)) maps to
GraphQL as follows. These are *conventions*; your GraphQL schema's actual
naming is up to you, but a consistent mapping keeps the builder simple.

### Entity → GraphQL type / root field

| Ontology `Entity.type` | GraphQL |
|------------------------|---------|
| `Order` | object type `Order`; collection root field `orders(...)` |
| `Product` | object type `Product`; collection root field `products(...)` |
| `LineItem` | object type `LineItem`; nested under `order { lineItems }` or `product { lineItems }` |

Convention: PascalCase entity type → same PascalCase GraphQL type;
lowerCamel pluralized root field for the collection.

### Field → GraphQL field / scalar

| Ontology `Field.type` | GraphQL scalar / selection |
|-----------------------|----------------------------|
| `scalar` (no `unit`) | `String` / `Int` / `Float` / `Boolean` leaf field |
| `scalar` with `unit: "USD"` | money leaf field (e.g. `totalAmount`), `Float`/`Int` cents |
| `scalar` with `unit: "count"` | `Int` leaf field (e.g. `quantity`) |
| `enum` (+`enum_values`) | GraphQL `enum` leaf field; values are the `enum_values` upper-cased |
| `date` | `String`/`DateTime` leaf field; sortable, range-filterable |
| `reference` | the entity's id leaf field (e.g. `orderId`) |

Convention: ontology `snake_case` field name → GraphQL `lowerCamelCase`
(`total_amount` → `totalAmount`, `order_id` → `orderId`).

### Relationship (cardinality) → nested selection

| `Relationship.cardinality` | GraphQL nested selection |
|----------------------------|--------------------------|
| `one-to-one` | singular nested object: `order { ... }` |
| `one-to-many` | plural nested connection/list: `lineItems { ... }` |
| `many-to-many` | plural nested connection, often paginated: `tags(first: N) { ... }` |

### `allowed_aggregations` → aggregate fields / arguments

| Ontology aggregation | GraphQL aggregate selection (convention) |
|----------------------|------------------------------------------|
| `sum` | `aggregate { sum { <field> } }` |
| `avg` | `aggregate { avg { <field> } }` |
| `min` / `max` | `aggregate { min { <field> } }` / `max { <field> }` |
| `count` | `aggregate { count }` (or `count { <field> }`) |
| group-by | `aggregate(groupBy: [<field>]) { ... }` |

**Hard rule:** a plain record count — `count` over the entity's identity (a
`reference` field) — is always available and needs no `allowed_aggregations`
entry. For every **value aggregation** (`sum`/`avg`/`min`/`max`, and `count` on
a dimension/enum field), only emit the aggregate selection if that aggregation
is in the field's `allowed_aggregations`. Anything else is a builder error that
must surface as `AGGREGATION_NOT_ALLOWED`
([`../SPEC.md`](../SPEC.md#error-model)), exactly as
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json)
does for the sales domain.

## The dynamic algorithm

Given `ontology` (a `schema` response) and `intent` (a parsed query plan):

1. **Resolve the target entity.** Look up `intent.entity` in `ontology.entities`.
   If absent → error (unknown entity).
2. **Select requested fields.** For each name in `intent.fields`, confirm it
   exists on the target entity; map it to its GraphQL leaf name. Drop/flag
   unknown fields.
3. **Expand relationships per intent/depth.** For each requested relationship,
   look it up in the entity's `relationships`, emit a nested selection whose
   plurality follows `cardinality`, and recurse into the target entity —
   bounded by `intent.depth` (default small, e.g. 2) to avoid unbounded trees.
4. **Apply filters / arguments.** Translate `intent.filters` into the
   collection root field's argument object. Validate enum filter values against
   the field's `enum_values`.
5. **Apply ONLY allowed aggregations.** For each `(field, op)` in
   `intent.aggregations`: a plain **record count** — `count` over the entity's
   identity (a `reference` field) — is always permitted and is *not* gated by
   `allowed_aggregations`. Every other combination is a **value aggregation**
   (`sum`/`avg`/`min`/`max`, and `count` on a dimension/enum field) and must
   satisfy `op ∈ field.allowed_aggregations`. If it does not →
   raise `AGGREGATION_NOT_ALLOWED` with the offending field, requested op, and
   the allowed set; **do not** silently drop or substitute. Emit the
   `aggregate { ... }` selection, including `groupBy` for any `intent.group_by`.
6. **Emit GraphQL.** Render the root field, arguments, leaf selections, nested
   relationship selections, and the aggregate block into a single GraphQL
   document string.

## Illustrative Python builder

> **Illustrative only.** This is a teaching reference, not a tracked module in
> this repo, and is intentionally not linted or tested by CI. Adapt it to your
> GraphQL schema and error-handling conventions.

```python
"""Build a GraphQL query string from an MCP-A `schema` ontology + a parsed intent.

Why: shows how structured-mode `query` turns the ontology guardrail into a
concrete GraphQL document, applying ONLY allowed_aggregations so structured
answers stay precise-by-construction (SPEC §Aggregation Correctness).
What: pure function (ontology dict, intent dict) -> GraphQL query string.
Test: feed the storefront ontology (examples/15-schema-graphql.response.json) and
a region-revenue intent; assert the output contains `groupBy: [region]`,
`sum { totalAmount }`, and `count`; assert requesting sum on a field whose
allowed_aggregations lacks "sum" raises AggregationNotAllowed.
"""
from __future__ import annotations


class AggregationNotAllowed(Exception):
    """Raised when an intent requests an aggregation the ontology forbids.

    Why: maps directly to the AGGREGATION_NOT_ALLOWED abstract error code; the
    builder must fail loudly instead of guessing (SPEC §Error Model).
    What: carries the offending field, the requested op, and the allowed set.
    Test: request `sum` on a field whose allowed_aggregations omits it; assert raised.
    """

    def __init__(self, field: str, op: str, allowed: list[str]) -> None:
        super().__init__(f"{op} not allowed on {field}; allowed: {allowed}")
        self.field = field
        self.op = op
        self.allowed = allowed


def _camel(name: str) -> str:
    """Why: ontology uses snake_case, GraphQL convention is lowerCamelCase.
    What: 'total_amount' -> 'totalAmount'.
    Test: assert _camel('order_id') == 'orderId' and _camel('name') == 'name'.
    """
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


def _index_fields(entity: dict) -> dict[str, dict]:
    """Why: O(1) lookup of a field's metadata (type, allowed_aggregations).
    What: returns {field_name: field_obj} for one entity.
    Test: index the Order entity; assert 'total_amount' in the result.
    """
    return {f["name"]: f for f in entity["fields"]}


def build_graphql(ontology: dict, intent: dict) -> str:
    """Why: the core of structured-mode GraphQL query construction.
    What: renders a GraphQL document from the ontology + parsed intent.
    Test: see module docstring — region-revenue intent over storefront ontology.
    """
    # 1. Resolve the target entity.
    entities = {e["type"]: e for e in ontology["entities"]}
    if intent["entity"] not in entities:
        raise ValueError(f"unknown entity: {intent['entity']}")
    entity = entities[intent["entity"]]
    fields = _index_fields(entity)
    root_field = _camel(intent["entity"]) + "s"  # naive pluralization

    # 4. Build the filter argument object from intent.filters.
    args = []
    for key, value in intent.get("filters", {}).items():
        if key not in fields:
            raise ValueError(f"unknown filter field: {key}")
        rendered = (
            "[" + ", ".join(str(v) for v in value) + "]"
            if isinstance(value, list)
            else f'"{value}"'
        )
        args.append(f"{_camel(key)}: {rendered}")
    arg_str = f"(filter: {{ {', '.join(args)} }})" if args else ""

    # 5. Apply ONLY allowed aggregations (the precision guardrail).
    agg_lines: list[str] = []
    group_by = [_camel(g) for g in intent.get("group_by", [])]
    if group_by:
        agg_lines.append(f"groupBy: [{', '.join(group_by)}]")
    for field_name, op in intent.get("aggregations", []):
        meta = fields.get(field_name)
        if meta is None:
            raise ValueError(f"unknown aggregation field: {field_name}")
        # Record-count convention: counting rows via the entity's identity
        # (a `reference` field) is ALWAYS available and is NOT gated by
        # allowed_aggregations. Only VALUE aggregations (sum/avg/min/max, and
        # count on dimension/enum fields) must appear in allowed_aggregations.
        is_record_count = op == "count" and meta.get("type") == "reference"
        allowed = meta.get("allowed_aggregations", [])
        if not is_record_count and op not in allowed:
            raise AggregationNotAllowed(field_name, op, allowed)
        if op == "count":
            agg_lines.append("count")
        else:
            agg_lines.append(f"{op} {{ {_camel(field_name)} }}")

    # 2 + 3. Leaf fields and (depth-bounded) relationship expansions.
    selections = [_camel(f) for f in intent.get("fields", [])]
    rels = {r["name"]: r for r in entity.get("relationships", [])}
    for rel_name in intent.get("expand", []):
        if rel_name in rels:
            selections.append(f"{_camel(rel_name)} {{ id }}")  # depth-bounded stub

    body_parts: list[str] = []
    if selections:
        body_parts.append("nodes { " + " ".join(selections) + " }")
    if agg_lines:
        body_parts.append("aggregate { " + " ".join(agg_lines) + " }")
    body = " ".join(body_parts) or "nodes { id }"

    # 6. Emit the GraphQL document.
    return f"query {{ {root_field}{arg_str} {{ {body} }} }}"
```

## Worked example: storefront revenue by region

Take the ontology from
[`../examples/15-schema-graphql.response.json`](../examples/15-schema-graphql.response.json)
and the intent parsed from the structured `query` in
[`../examples/16-query-graphql-structured.request.json`](../examples/16-query-graphql-structured.request.json)
(*"Total revenue and order count by region for paid and shipped orders this
quarter"*):

```python
intent = {
    "entity": "Order",
    "fields": [],
    "filters": {"status": ["PAID", "SHIPPED"]},
    "group_by": ["region"],
    "aggregations": [("total_amount", "sum"), ("order_id", "count")],
}
```

`Order.total_amount` declares `allowed_aggregations: ["sum","avg","min","max","count"]`,
so its `sum` is an allowed value aggregation. `Order.order_id` is a `reference`
field with no `allowed_aggregations`, but `("order_id", "count")` is a record
count over the entity's identity — always permitted and not gated by
`allowed_aggregations` — so both pass the step-5 guardrail.
`build_graphql(ontology, intent)` produces:

```graphql
query { orders(filter: { status: [PAID, SHIPPED] }) { aggregate { groupBy: [region] sum { totalAmount } count } } }
```

The GraphQL resolver computes the `sum` and `count` per region — deterministic,
server-side. The server maps each returned group back to a typed object in the
`query` response's `structured` array, exactly as in
[`../examples/16-query-graphql-structured.response.json`](../examples/16-query-graphql-structured.response.json):

```json
"structured": [
  { "region": "AMER", "order_count": 5128, "total_revenue": 2841500, "currency": "USD" }
]
```

and records the generated query as a citation snippet under
`source_system: "storefront-graphql"`.

**Now the failure case.** If the intent had asked for `("region", "sum")` —
summing an enum — step 5 finds `sum ∉ Order.region.allowed_aggregations`
(which is `["count"]`) and raises `AggregationNotAllowed`. The server returns
`AGGREGATION_NOT_ALLOWED` per [`../SPEC.md`](../SPEC.md#error-model), mirroring
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json).
It does not invent a number.

## The precision pillar

Aggregations in MCP-A are **computed, not estimated**.
[`../SPEC.md`](../SPEC.md#aggregation-correctness-conformance) (Aggregation
Correctness Conformance) requires:

> All advertised aggregations MUST be computed deterministically server-side via
> database queries, GraphQL resolvers, or direct computation over source data
> (not via learned model inference).

[`../CONFORMANCE.md`](../CONFORMANCE.md) carries the matching audit check. A
GraphQL backend satisfies this naturally: the `aggregate` resolver does the math.
The builder's only job is to ensure it asks for *only* the aggregations the
ontology promised — which is why step 5 is the heart of this guide.

## See also

- [`surfacing-apis.md`](./surfacing-apis.md) — where this builder fits in the end-to-end flow (step 3.2).
- [`intent-and-query-building.md`](./intent-and-query-building.md) — how the `intent` dict is produced.
- [`../schemas/schema.response.json`](../schemas/schema.response.json) — the ontology contract this consumes.
