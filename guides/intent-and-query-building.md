---
Status: DRAFT
Version: 1.0.1-beta
Date: 2026-06-23
---

# Instructing LLMs: Intent Classification & Query Building

> **Status: non-normative guide.** This document is explanatory implementation
> guidance complementing [`../SPEC.md`](../SPEC.md). It is not part of the
> behavior contract; where it differs from the SPEC or
> [`../schemas/`](../schemas/), those win. The prompt templates below are
> starting points to adapt, not normative requirements — but the JSON shapes
> their outputs must conform to (`RoutingDecision`, the query response, etc.)
> **are** governed by [`../schemas/`](../schemas/).

## The division of labor

MCP-A splits work across two models, and the prompts you write depend on which
side you are on. From [`../SPEC.md`](../SPEC.md#design-principles) (Efficiency
pillar and Design Principle 1):

> It uses a less expensive inference model to classify, structure, and compile
> the response, so the expensive client-side model does less work. Cheap model
> structures; expensive model consumes a finished result.

Concretely:

| Side | Model | Responsibilities |
|------|-------|------------------|
| **Server** | cheap | Classify the question's intent · route to domain(s) · build the backend query (GraphQL/REST/SQL) · structure and consolidate the typed output |
| **Client** | expensive | Formulate the natural-language question · decide which primitive to call · consume the compiled answer |

So the two prompts that matter most are **server-side**: intent
classification/routing (template A) and query building (template B). The
client-side prompt (template C) is optional — it only decides *which primitive
to call*; it never builds queries.

Each template below has a short rationale, the prompt text, and a worked
input→output. All outputs are aligned to real schema field names.

---

## Template A — Server-side intent classification & routing

**Rationale.** Before the server can build any query, it must decide *what the
question is asking* and *which domain(s) own the answer*. The output is a routing
decision the server acts on and later surfaces through `explain`. Its shape must
match `RoutingDecision` in
[`../schemas/common.defs.json`](../schemas/common.defs.json): required
`rationale`; optional `algorithm`, `alternative_routings[{domains, score,
reason?}]`, `reused_prior_routing`.

**Prompt.**

```text
You are the routing model inside an MCP-A server. You DO NOT answer the question.
You decide which information domain(s) should answer it and explain why.

You are given:
- DOMAIN CATALOG: the JSON `domains` array from a `discover` response. Each domain
  has id, name, description, example_questions, and source_systems.
- QUESTION: the user's natural-language question.

Output ONLY a JSON object with these keys:
- question_classified_as: a short kebab-case label for the question's intent.
- domains_considered: array of domain ids you evaluated.
- routing_decision: an object with:
    - algorithm: "semantic-match"
    - rationale: one or two sentences on why the chosen domain(s) own this answer.
    - alternative_routings: array of { domains: [id...], score: 0.0-1.0, reason }
      including the option you chose (highest score) and any you rejected.
    - reused_prior_routing: false

Rules:
- Choose the FEWEST domains that fully cover the question. Prefer one.
- A domain qualifies only if its description/fields plausibly own the data asked for.
- Never invent a domain id that is not in the catalog.
- Output valid JSON and nothing else.
```

**Worked example.** Input catalog =
[`../examples/14-discover-graphql.response.json`](../examples/14-discover-graphql.response.json)
`domains`; QUESTION = *"Total revenue and order count by region for paid and
shipped orders this quarter"*. Expected output:

```json
{
  "question_classified_as": "revenue-and-order-volume-rollup-by-region",
  "domains_considered": ["storefront"],
  "routing_decision": {
    "algorithm": "semantic-match",
    "rationale": "The question is a revenue-and-volume rollup over orders. storefront owns Order.total_amount and Order.status and computes sum/count deterministically through its GraphQL aggregate resolver, so it is queried directly.",
    "alternative_routings": [
      { "domains": ["storefront"], "score": 0.93, "reason": "Single-domain routing resolves the region group-by, status filter, and sum/count aggregations server-side in one GraphQL query." }
    ],
    "reused_prior_routing": false
  }
}
```

This is exactly the `routing_decision` that appears in
[`../examples/16-query-graphql-structured.response.json`](../examples/16-query-graphql-structured.response.json)
and that `explain` echoes in
[`../examples/18-explain-graphql.response.json`](../examples/18-explain-graphql.response.json).

---

## Template B — Server-side query building (intent → query plan)

**Rationale.** Once routed, the server turns the question into a structured
**query plan** that the GraphQL builder
([`graphql-query-builder.md`](./graphql-query-builder.md)) renders into a GraphQL
document. The model never writes GraphQL — it emits a plan constrained by the
domain's ontology, so the deterministic builder (not the LLM) produces the query.
The hard constraint: **aggregations MUST be drawn only from each field's
`allowed_aggregations`.** This is what keeps structured answers precise and is
what lets the builder raise `AGGREGATION_NOT_ALLOWED` deterministically.

**Prompt.**

```text
You are the query-planning model inside an MCP-A server. You DO NOT answer the
question and you DO NOT write GraphQL. You emit a structured query plan.

You are given:
- ONTOLOGY: the JSON from a `schema` response for the chosen domain (entities with
  fields, types, units, allowed_aggregations, enum_values, and relationships).
- QUESTION: the user's natural-language question.

Output ONLY a JSON object:
- entity: the target Entity.type from the ontology.
- fields: array of non-aggregated field names to return (may be empty for pure rollups).
- filters: object of { field_name: value-or-array } using only ontology fields;
  enum values must be from that field's enum_values.
- group_by: array of field names to group by (use enum/category/date fields).
- aggregations: array of [field_name, op] pairs. A record count — [id_field, "count"]
  over a `reference` identity field — is always allowed and needs no
  allowed_aggregations entry. Any other op MUST be present in that field's
  allowed_aggregations. If the question needs a value aggregation the ontology
  does not allow, set "error": "AGGREGATION_NOT_ALLOWED" with the offending
  field and op, and omit aggregations.
- expand: array of relationship names to expand (only if the question needs them).

Rules:
- Use only entities, fields, relationships, and aggregations the ontology declares.
- NEVER request an aggregation absent from allowed_aggregations — flag it instead.
- Keep the plan minimal: just what the question asks for.
- Output valid JSON and nothing else.
```

**Worked example.** Input ONTOLOGY =
[`../examples/15-schema-graphql.response.json`](../examples/15-schema-graphql.response.json);
QUESTION = *"Total revenue and order count by region for paid and shipped orders
this quarter"*. Expected output:

```json
{
  "entity": "Order",
  "fields": [],
  "filters": { "status": ["PAID", "SHIPPED"] },
  "group_by": ["region"],
  "aggregations": [["total_amount", "sum"], ["order_id", "count"]],
  "expand": []
}
```

`total_amount` allows `sum`, and `["order_id", "count"]` is a record count over
the identity field (always permitted, not gated by `allowed_aggregations`), so the
plan is valid and feeds straight into `build_graphql(...)` from
[`graphql-query-builder.md`](./graphql-query-builder.md).

**Failure variant.** QUESTION = *"What's the sum of order regions?"* — the model
must refuse the impossible aggregation:

```json
{
  "entity": "Order",
  "error": "AGGREGATION_NOT_ALLOWED",
  "offending_field": "region",
  "requested_op": "sum",
  "allowed": ["count"]
}
```

The server then returns the `AGGREGATION_NOT_ALLOWED` error
([`../SPEC.md`](../SPEC.md#error-model)) rather than a fabricated number, mirroring
[`../examples/07-error-aggregation.response.json`](../examples/07-error-aggregation.response.json).

---

## Template C — (Optional) Client-side primitive selection

**Rationale.** On the client, the expensive model decides *which primitive to
call* and how to shape the request — it does not classify intent server-side or
build queries. The main decisions: `query` vs `schema` vs `action`, and whether
to set `response_schema` (prose vs typed output). Request shapes are governed by
[`../schemas/query.request.json`](../schemas/query.request.json),
[`../schemas/schema.request.json`](../schemas/schema.request.json), and
[`../schemas/action.request.json`](../schemas/action.request.json).

**Prompt.**

```text
You are an agent talking to an MCP-A server that exposes seven tools: discover,
schema, query, action, follow_up, context, explain. Choose the ONE tool to call
next and produce its JSON arguments.

Decision guide:
- Use `discover` if you don't yet know which domains exist.
- Use `schema` if you need a domain's entities/fields/allowed_aggregations before
  asking for typed output (target: "domain").
- Use `query` to ASK a question (read). Set response_schema
  { kind: "domain", value: "<domain_id>" } when you need typed/structured values
  or server-side aggregations; omit it for a prose answer.
- Use `action` to CHANGE something (write): pass a natural-language `request`.
- Use `follow_up` to refine or poll a prior answer_id without re-asking.
- Use `explain` to inspect how a prior answer_id was routed.

Always include user_id. Output ONLY the chosen tool name and its JSON arguments.
```

**Worked example.** The agent wants typed revenue numbers and has already seen
the `storefront` ontology. Expected output:

```text
tool: query
arguments:
{
  "question": "Total revenue and order count by region for paid and shipped orders this quarter",
  "user_id": "u-8842",
  "response_schema": { "kind": "domain", "value": "storefront" },
  "options": { "include_prose": true, "include_confidence": true }
}
```

This is precisely
[`../examples/16-query-graphql-structured.request.json`](../examples/16-query-graphql-structured.request.json).
Had the agent wanted to *create* the discount code instead, it would have chosen
`action` with the request from
[`../examples/17-action-graphql.request.json`](../examples/17-action-graphql.request.json).

## See also

- [`surfacing-apis.md`](./surfacing-apis.md) — where templates A and B run in the server flow (steps 3.1–3.2).
- [`graphql-query-builder.md`](./graphql-query-builder.md) — consumes template B's query plan.
- [`../SPEC.md`](../SPEC.md#design-principles) — the division-of-labor principles (normative).
