---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-23
---

# Surfacing a REST Backend beneath MCP-A

> **Status: non-normative guide.** This document is explanatory implementation
> guidance complementing [`../SPEC.md`](../SPEC.md). It is not part of the
> behavior contract; where it differs from the SPEC or
> [`../schemas/`](../schemas/), those win. The Python snippet below is
> **illustrative** — a readable reference to copy and adapt, **not** a
> maintained module shipped with this repo.

You have a REST API — collections like `/tickets`, `/customers`, sub-resources
like `/tickets/{id}/comments` — and you want an agent to get fast, precise, cited
answers out of it. This guide shows how to put that REST API *behind* MCP-A so
the client only ever sees the seven primitives
([`surfacing-apis.md`](./surfacing-apis.md)): the client calls `query`; the
server calls REST.

A `query` with `response_schema` set asks the server for typed values. To get
them from a REST backend, the server plans an **HTTP request sequence**
dynamically from two inputs:

1. The domain's **ontology** — exactly what the `schema` primitive returns
   ([`../schemas/schema.response.json`](../schemas/schema.response.json)):
   entities, fields (with `type`, `unit`, `nullable`, `allowed_aggregations`,
   `enum_values`), and relationships (with `cardinality`).
2. A **parsed intent** — the structured query plan produced by the server-side
   query-building model (target entity, requested fields, filters, group-by,
   aggregations). See
   [`intent-and-query-building.md`](./intent-and-query-building.md), template B,
   for how that plan is produced.

The ontology is the **guardrail**: the planner may only emit fields and
aggregations the ontology declares. The crucial difference from the GraphQL and
SQL backends is that **REST has no native aggregation**. There is no `aggregate`
resolver and no `GROUP BY`. So when an aggregation is requested, the server
**fetches the matching rows and reduces them deterministically server-side** —
which is exactly what
[`../SPEC.md`](../SPEC.md#aggregation-correctness-conformance) (Aggregation
Correctness Conformance) and [`../CONFORMANCE.md`](../CONFORMANCE.md) require:

> All advertised aggregations MUST be computed deterministically server-side via
> database queries, GraphQL resolvers, or direct computation over source data
> (not via learned model inference).

"Direct computation over source data" is the REST case. The aggregation is still
**computed, not estimated** — it just runs in the MCP-A server's own code after
the fetch rather than in the backend.

## Mapping tables: ontology → REST

These are *conventions*; your REST API's actual routes and parameters are up to
you, but a consistent mapping keeps the planner simple.

### Entity → REST resource / collection

| Ontology `Entity.type` | REST |
|------------------------|------|
| `Ticket` | collection `GET /tickets`; single `GET /tickets/{id}` |
| `Customer` | collection `GET /customers`; single `GET /customers/{id}` |
| `Comment` | nested sub-resource `GET /tickets/{id}/comments` |

Convention: a top-level PascalCase entity type → its lower pluralized
collection path (`Ticket` → `/tickets`). A nested sub-resource — one nothing
references by foreign key, reachable only through a parent's one-to-many
relationship — resolves to the parent path instead
(`Comment` → `/tickets/{id}/comments`), *not* a naive top-level `/comments`.

### Field → response projection / query params

| Ontology `Field.type` | REST handling |
|-----------------------|---------------|
| `scalar` (no `unit`) | leaf field in the JSON body; selectable via `?fields=` |
| `scalar` with `unit: "USD"` / `"count"` | numeric leaf field; selectable via `?fields=` |
| `enum` (+`enum_values`) | leaf field; usable as an equality/`IN` filter param (`?status=open`) |
| `date` | leaf field; usable as a range filter (`?created_at[gte]=...`) and `sort` key |
| `reference` | the resource id (`ticket_id`) or a foreign-key filter (`?customer_id=...`) |

Convention: ontology field name → same JSON key; restrict the payload with
`?fields=ticket_id,priority` so you fetch only what the plan needs.

### Relationship (cardinality) → sub-resource or expansion

| `Relationship.cardinality` | REST handling |
|----------------------------|---------------|
| `one-to-one` | `?expand=customer` / `?include=customer`, or a follow-up `GET /customers/{id}` |
| `one-to-many` | nested collection `GET /tickets/{id}/comments`, or `?include=comments` |
| `many-to-many` | nested paginated collection, often via a join route `GET /tickets/{id}/tags` |

### `allowed_aggregations` → fetch + server-side reduce

| Ontology aggregation | REST handling (convention) |
|----------------------|----------------------------|
| `sum` | `GET` the matching rows (projected), then `sum()` the field in server code |
| `avg` | fetch rows, then compute `sum()/len()` server-side |
| `min` / `max` | fetch rows, then `min()` / `max()` server-side |
| `count` | fetch matching rows and count them (or read a `total` from a paginated envelope) |
| group-by | bucket fetched rows by the group field in server code, then reduce each bucket |

**Hard rule (same as every backend):** a plain record count — `count` over the
entity's identity (a `reference` field) — is always available and needs no
`allowed_aggregations` entry. For every **value aggregation** (`sum`/`avg`/`min`/
`max`, and `count` on a dimension/enum field), only compute it if that
aggregation is in the field's `allowed_aggregations`. Anything else is a planner
error that must surface as `AGGREGATION_NOT_ALLOWED`
([`../SPEC.md`](../SPEC.md#error-model)), exactly as
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json)
does for the sales domain. Note the **cost/precision tradeoff**: because REST has
no native rollup, a value aggregation may fetch many rows. The planner should
project narrowly (`?fields=`), paginate, and filter server-side-first; the
precision is non-negotiable, but the fetch cost is real and worth bounding.

## The REST request planner

Given `ontology` (a `schema` response) and `intent` (a parsed query plan):

1. **Resolve the target collection.** Look up `intent.entity` in
   `ontology.entities`; if absent → error (unknown entity). Map a top-level
   entity to its own collection path (`Ticket` → `/tickets`). Map a nested
   sub-resource — an entity nothing references by foreign key, reachable only via
   a parent's one-to-many relationship — to its nested path
   (`Comment` → `/tickets/{id}/comments`).
2. **Select fields / projection.** For each name in `intent.fields` (plus any
   field needed for filtering, grouping, or aggregating), confirm it exists on
   the entity and add it to a `?fields=` projection so the payload stays small.
3. **Apply filters and pagination.** Translate `intent.filters` into query
   params (`?status=open`), validating enum values against `enum_values`. Add
   `?page`/`?per_page` (or cursor) params so large result sets are fetched in
   bounded pages.
4. **Expand relationships per intent/depth.** For each requested relationship,
   either add `?expand=`/`?include=` or plan a nested sub-resource call
   (`/tickets/{id}/comments`) whose plurality follows `cardinality`.
5. **For aggregations, fetch the rows and reduce server-side.** A plain record
   **count** over the entity's identity (a `reference` field) is always permitted
   and is *not* gated by `allowed_aggregations`. Every other combination is a
   **value aggregation** and must satisfy `op ∈ field.allowed_aggregations`; if
   not → raise `AGGREGATION_NOT_ALLOWED` with the offending field, op, and the
   allowed set. Then fetch the matching (projected, paginated) rows and compute
   the reduction in server code — bucketing by `intent.group_by` first if a
   group-by is requested. (Note the cost: this is the fetch-and-reduce tradeoff.)
6. **Emit the REST call sequence.** Render the planned calls — each a
   `(method, path, params)` triple — in execution order: the list/collection
   fetches first, then any per-row relationship expansions.

## Illustrative Python planner

> **Illustrative only.** This is a teaching reference, not a tracked module in
> this repo, and is intentionally not linted or tested by CI. Adapt it to your
> REST routes, pagination scheme, and error-handling conventions.

```python
"""Plan the REST request(s) for a structured query from an MCP-A ontology + intent.

Why: shows how structured-mode `query` turns the ontology guardrail into a
concrete REST fetch plan, applying ONLY allowed_aggregations and computing value
aggregations by fetching rows and reducing server-side, since REST has no native
aggregation (SPEC §Aggregation Correctness).
What: pure function (ontology dict, intent dict) -> list of REST requests, each a
{"method", "path", "params"} dict, plus a server-side reduce note.
Test: feed the support-desk ontology (examples/20-schema-rest.response.json) and
an open-tickets-by-priority intent; assert the plan GETs /tickets with
status=open and a fields projection, and that the reduce step counts ticket_id
grouped by priority; assert summing an enum (e.g. ["status","sum"]) raises
AggregationNotAllowed.
"""
from __future__ import annotations


class AggregationNotAllowed(Exception):
    """Raised when an intent requests an aggregation the ontology forbids.

    Why: maps directly to the AGGREGATION_NOT_ALLOWED abstract error code; the
    planner must fail loudly instead of guessing (SPEC §Error Model).
    What: carries the offending field, the requested op, and the allowed set.
    Test: request `sum` on a field whose allowed_aggregations omits it; assert raised.
    """

    def __init__(self, field: str, op: str, allowed: list[str]) -> None:
        super().__init__(f"{op} not allowed on {field}; allowed: {allowed}")
        self.field = field
        self.op = op
        self.allowed = allowed


def _pluralize(entity_type: str) -> str:
    """Why: collection segments are the lowercased plural of the entity type.
    What: 'Ticket' -> 'tickets' (naive lowercase pluralization).
    Test: assert _pluralize('Customer') == 'customers'.
    """
    return entity_type.lower() + "s"


def _identity(entity: dict) -> str:
    """Why: an entity's identity (its first `reference` field) is both how a
    parent points a foreign key at it and how we test whether it is referenced.
    What: returns the first `reference` field name (e.g. Ticket -> 'ticket_id').
    Test: assert _identity(ticket_entity) == 'ticket_id'.
    """
    for f in entity["fields"]:
        if f["type"] == "reference":
            return f["name"]
    raise ValueError(f"entity {entity['type']} has no reference identity field")


def _collection_path(ontology: dict, entity_type: str) -> str:
    """Why: a top-level entity lives at its own collection, but a nested
    sub-resource is only reachable through its parent — naive pluralization
    (`Comment` -> `/comments`) would emit a route the backend does not expose.
    What: returns '/{collection}' for a top-level entity (something points a
    foreign key at it), or '/{parent_collection}/{id}/{child_collection}' for a
    sub-resource (nothing references it; it hangs off a parent's one-to-many).
    Test: _collection_path(ont, 'Ticket') == '/tickets';
    _collection_path(ont, 'Comment') == '/tickets/{id}/comments'.
    """
    entities = {e["type"]: e for e in ontology["entities"]}
    my_id = _identity(entities[entity_type])

    # If any OTHER entity carries this entity's identity as a foreign key, the
    # entity is addressed directly and is therefore top-level.
    referenced = any(
        other["type"] != entity_type
        and any(f["name"] == my_id and f["type"] == "reference" for f in other["fields"])
        for other in entities.values()
    )
    if referenced:
        return "/" + _pluralize(entity_type)

    # Otherwise nest under the parent that owns it via a one-to-many relationship.
    for parent in entities.values():
        if parent["type"] == entity_type:
            continue
        for rel in parent.get("relationships", []):
            if rel["target_entity"] == entity_type and rel["cardinality"] == "one-to-many":
                return f"/{_pluralize(parent['type'])}/{{id}}/{_pluralize(entity_type)}"

    return "/" + _pluralize(entity_type)  # no parent found: treat as top-level


def _index_fields(entity: dict) -> dict[str, dict]:
    """Why: O(1) lookup of a field's metadata (type, allowed_aggregations).
    What: returns {field_name: field_obj} for one entity.
    Test: index the Ticket entity; assert 'priority' in the result.
    """
    return {f["name"]: f for f in entity["fields"]}


def plan_rest(ontology: dict, intent: dict) -> dict:
    """Why: the core of structured-mode REST request planning.
    What: returns {"requests": [...], "reduce": {...} | None} — the HTTP calls to
    issue and the server-side reduction to run over the fetched rows.
    Test: see module docstring — open-tickets-by-priority over support-desk.
    """
    # 1. Resolve the target collection.
    entities = {e["type"]: e for e in ontology["entities"]}
    if intent["entity"] not in entities:
        raise ValueError(f"unknown entity: {intent['entity']}")
    entity = entities[intent["entity"]]
    fields = _index_fields(entity)
    path = _collection_path(ontology, intent["entity"])

    # 5 (validation half). Gate aggregations BEFORE fetching anything.
    reduce_ops: list[tuple[str, str]] = []
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
        reduce_ops.append((field_name, op))

    # 2 + 3 + 4. Build the projection, filters, and expansions into params.
    params: dict[str, object] = {}
    projection = list(intent.get("fields", []))
    projection += [g for g in intent.get("group_by", []) if g not in projection]
    projection += [f for f, _ in reduce_ops if f not in projection]
    if projection:
        params["fields"] = ",".join(projection)
    for key, value in intent.get("filters", {}).items():
        if key not in fields:
            raise ValueError(f"unknown filter field: {key}")
        params[key] = ",".join(map(str, value)) if isinstance(value, list) else value
    params["per_page"] = 200  # bound the fetch; the caller paginates to exhaustion
    expand = [r for r in intent.get("expand", [])]
    if expand:
        params["expand"] = ",".join(expand)

    requests = [{"method": "GET", "path": path, "params": params}]

    # 5 (compute half). Describe the deterministic server-side reduction. REST has
    # no native aggregation, so the server runs this over the fetched rows.
    reduce = None
    if reduce_ops:
        reduce = {
            "group_by": intent.get("group_by", []),
            "ops": reduce_ops,  # e.g. [("ticket_id", "count")]
        }
    return {"requests": requests, "reduce": reduce}
```

## Worked example: open tickets by priority

Take the ontology from
[`../examples/20-schema-rest.response.json`](../examples/20-schema-rest.response.json)
and the intent parsed from the structured `query` in
[`../examples/21-query-rest.request.json`](../examples/21-query-rest.request.json)
(*"How many open tickets do we have right now, broken down by priority?"*):

```python
intent = {
    "entity": "Ticket",
    "fields": [],
    "filters": {"status": "open"},
    "group_by": ["priority"],
    "aggregations": [("ticket_id", "count")],
}
```

`("ticket_id", "count")` is a record count over the entity's identity (a
`reference` field) — always permitted, not gated by `allowed_aggregations` — so
it passes the step-5 guard. `plan_rest(ontology, intent)` produces:

```json
{
  "requests": [
    { "method": "GET", "path": "/tickets",
      "params": { "fields": "priority,ticket_id", "status": "open", "per_page": 200 } }
  ],
  "reduce": { "group_by": ["priority"], "ops": [["ticket_id", "count"]] }
}
```

The server pages through `/tickets?status=open`, projecting only `priority` and
`ticket_id`, then buckets the fetched rows by `priority` and counts each bucket —
**deterministic, server-side, computed not estimated**. It maps each bucket back
to a typed object in the `query` response's `structured` array, exactly as in
[`../examples/21-query-rest.response.json`](../examples/21-query-rest.response.json):

```json
"structured": [
  { "priority": "urgent", "ticket_count": 12 },
  { "priority": "high",   "ticket_count": 47 }
]
```

and records the REST call sequence as a citation snippet under
`source_system: "support-rest"`, alongside a `routing_decision`.

**Now the failure case.** If the intent had asked for `("status", "sum")` —
summing an enum — step 5 finds `sum ∉ Ticket.status.allowed_aggregations` (which
is `["count"]`) and raises `AggregationNotAllowed`. The server returns
`AGGREGATION_NOT_ALLOWED` per [`../SPEC.md`](../SPEC.md#error-model), mirroring
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json).
It does not fetch rows and invent a number.

## The write case: REST writes → `action`

Reads map to `query`; **writes map to the `action` primitive**
([`../SPEC.md`](../SPEC.md#7-action)). A natural-language `action` request is
interpreted server-side and turned into REST mutations:

| HTTP method | Typical `ActionEffect.kind` |
|-------------|-----------------------------|
| `POST` (create) | `created` |
| `PUT` / `PATCH` (update) | `updated` (or `invoked` for a state transition) |
| `DELETE` | `deleted` |
| any side-effecting call | `invoked` |

Each effect carries `resource`, `source_system`, an optional `entity_id`, and a
`detail` object — a natural place to record the `method` and `path`. The worked
write is *"Reply to ticket 4821 …"* in
[`../examples/22-action-rest.request.json`](../examples/22-action-rest.request.json):
the server `POST`s a comment (a `created` effect) and `PATCH`es the ticket status
(an `invoked` effect), both on `support-rest`, returning `status: "completed"` —
see
[`../examples/22-action-rest.response.json`](../examples/22-action-rest.response.json).

## See also

- [`surfacing-apis.md`](./surfacing-apis.md) — where this planner fits in the end-to-end flow (step 3.2).
- [`sql-query-builder.md`](./sql-query-builder.md) — the SQL backend, where aggregation is native.
- [`graphql-query-builder.md`](./graphql-query-builder.md) — the GraphQL backend builder this mirrors.
- [`intent-and-query-building.md`](./intent-and-query-building.md) — how the `intent` dict is produced.
- [`../schemas/schema.response.json`](../schemas/schema.response.json) — the ontology contract this consumes.
