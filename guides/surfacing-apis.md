---
Status: DRAFT
Version: 1.0.1-beta
Date: 2026-06-23
---

# Surfacing an Underlying API beneath MCP-A

> **Status: non-normative guide.** This document is explanatory implementation
> guidance complementing [`../SPEC.md`](../SPEC.md). It is not part of the
> behavior contract; where it differs from the SPEC or
> [`../schemas/`](../schemas/), those win. The server-side config shapes shown
> here (the "domain→backend binding") are an illustrative convention the spec
> does **not** define — see [`../CONFORMANCE.md`](../CONFORMANCE.md) for actual
> requirements.

You have an existing API — a GraphQL endpoint, a REST service, a SQL warehouse —
and you want an agent to get fast, precise, cited answers out of it without
hand-orchestrating raw calls. This guide shows how to put that API *behind*
MCP-A. The running example is a storefront commerce GraphQL API; the same shape
applies to REST and SQL (see [REST and SQL backends](#rest-and-sql-backends)).

## The canonical-tools model

The single most important idea: **the seven MCP-A primitives are the MCP tools a
client sees.** A client that lists tools sees `discover`, `schema`, `query`,
`action`, `follow_up`, `context`, and `explain` — and nothing about your
GraphQL schema, your REST routes, or your SQL tables.

[`../SPEC.md`](../SPEC.md#relationship-to-mcp--lower-level-protocols) is explicit:

> **Key principle**: Every MCP-A server is a conformant MCP server. MCP-A
> defines specific tools (the **seven primitives**: discover, schema, query,
> action, follow_up, context, explain) and result shapes on top of MCP's base
> contract.

and:

> - **MCP tools** (e.g., `read_file`, `search_docs`) are *source systems* that
>   MCP-A can fan out to.
> - **MCP-A query** might route to the "codebase-search" domain, which
>   internally calls MCP tools and consolidates results.
>
> In other words, MCP-A wraps and orchestrates deterministic tool-calling to
> provide dynamic, personalized, explainable compiled answers.

So your GraphQL API is a **source system**, reached through a **domain**, called
**server-side** inside the implementation of `query`/`action`. The client never
calls GraphQL. It calls `query`; the server calls GraphQL. This is the
**Compile Server-Side; Hand the LLM a Finished Result** design principle
([`../SPEC.md`](../SPEC.md#design-principles)) made concrete.

```
Client (expensive model)                MCP-A server (cheap model)         Backend
  │  tools/list → 7 primitives                                              
  │  query("revenue by region") ───────► classify intent                    
  │                                       route to "storefront" domain       
  │                                       build GraphQL query ──────────────► storefront-graphql
  │                                       consolidate + cite ◄────────────── result
  │  ◄────────── compiled answer + citations + answer_id                     
```

## Registering the seven primitives as MCP tools

Because every MCP-A server *is* an MCP server, you expose the primitives the
ordinary MCP way: `tools/list` returns one tool per primitive, each tool's
`inputSchema` is that primitive's request schema from
[`../schemas/`](../schemas/), and the result shape is the corresponding response
schema. The files in [`../schemas/`](../schemas/) are the source of truth for
these shapes.

The following `tools/list`-style registration is **illustrative** (it omits five
primitives for brevity and uses `$ref` to the published schema `$id`s):

```json
{
  "tools": [
    {
      "name": "query",
      "description": "Ask a natural-language question over an MCP-A domain. The server classifies intent, fans out to the domain's source systems, and returns one compiled, cited answer (optionally typed when response_schema is supplied).",
      "inputSchema": { "$ref": "https://mcp-a.dev/schemas/query.request.json" },
      "outputSchema": { "$ref": "https://mcp-a.dev/schemas/query.response.json" }
    },
    {
      "name": "schema",
      "description": "Return a domain's ontology: entities, fields, types, units, allowed aggregations, and relationships.",
      "inputSchema": { "$ref": "https://mcp-a.dev/schemas/schema.request.json" },
      "outputSchema": { "$ref": "https://mcp-a.dev/schemas/schema.response.json" }
    },
    {
      "name": "action",
      "description": "Execute a state-changing operation over a domain (server maps it to a backend mutation/write).",
      "inputSchema": { "$ref": "https://mcp-a.dev/schemas/action.request.json" },
      "outputSchema": { "$ref": "https://mcp-a.dev/schemas/action.response.json" }
    },
    {
      "name": "discover",
      "description": "List the RBAC-filtered domains this user can ask about.",
      "inputSchema": { "$ref": "https://mcp-a.dev/schemas/discover.request.json" },
      "outputSchema": { "$ref": "https://mcp-a.dev/schemas/discover.response.json" }
    }
  ]
}
```

Many MCP runtimes want an inlined `inputSchema` rather than a `$ref`. In that
case, embed the contents of each request schema directly. Whatever you inline
MUST stay byte-faithful to [`../schemas/`](../schemas/); the schemas are the
contract.

## The domain → backend binding (non-normative convention)

MCP-A defines what a *domain* looks like to a client (an entry in `discover`
with an `id`, `source_systems`, `freshness_seconds`, etc.) but it deliberately
says **nothing** about how a server maps a domain to a concrete backend. That
mapping is a private server-side concern. The following "binding" is a
**non-normative convention** — one reasonable way to wire it; the spec does not
define or require it, and it is **invisible to clients**.

```yaml
# server-side config — NOT part of MCP-A, never sent to clients
domains:
  storefront:
    backend:
      kind: graphql                     # graphql | rest | sql
      endpoint: https://api.example.com/storefront/graphql
      auth: service-account:storefront  # server-side credential ref
    ontology_ref: storefront@2026-06-01 # what `schema` returns for this domain
    source_systems: ["storefront-graphql"]   # surfaced verbatim in discover
    actions:
      create_discount:
        mutation: discountCreate        # GraphQL mutation behind the action
```

Two things to note about how this private binding *surfaces*:

- The only part a client ever sees is `source_systems`. In
  [`../examples/14-discover-graphql.response.json`](../examples/14-discover-graphql.response.json)
  the `storefront` domain advertises `"source_systems": ["storefront-graphql"]`.
  That string is opaque provenance — it tells the client *that* a GraphQL
  backend is involved, not *where* it is or *how* to call it.
- `explain` may name the same source system in `domains_queried` and
  `source_latencies`/`confidence_per_source`
  (see [`../examples/18-explain-graphql.response.json`](../examples/18-explain-graphql.response.json)),
  again as provenance, never as a callable handle.

Everything else in the binding — endpoint URL, credentials, the
mutation-name mapping — stays server-side. Swapping `storefront` from GraphQL to
REST is a config change with **zero client impact**, because the client only
ever spoke the seven primitives.

## End-to-end GraphQL flow

Here is the full path for a structured `query`, cross-linked to the worked
example files:

1. **discover** — the client lists domains and finds `storefront` with
   `source_systems: ["storefront-graphql"]`, `status: "active"`, and
   `freshness_seconds: 120`.
   → [`14-discover-graphql.request.json`](../examples/14-discover-graphql.request.json)
   / [`14-discover-graphql.response.json`](../examples/14-discover-graphql.response.json)

2. **schema** — the client introspects the `storefront` ontology: `Product`,
   `Order`, `LineItem`, their fields/types/units, `allowed_aggregations`, and
   relationships. This is the input the query builder consumes.
   → [`15-schema-graphql.request.json`](../examples/15-schema-graphql.request.json)
   / [`15-schema-graphql.response.json`](../examples/15-schema-graphql.response.json)

3. **query** — the client asks *"Total revenue and order count by region for
   paid and shipped orders this quarter"* with
   `response_schema: {kind: "domain", value: "storefront"}`. Now the server does
   its work:
   1. The cheap server-side model **classifies intent** (a revenue+volume
      rollup) and **routes** to `storefront`
      (see [`intent-and-query-building.md`](./intent-and-query-building.md), template A).
   2. The server **builds a GraphQL query** from the step-2 ontology + the
      parsed intent — selecting `Order.total_amount`/`Order.order_id`, grouping
      by `region`, filtering on `status`, summing `total_amount` (an allowed
      value aggregation) and counting `order_id` (a record count)
      (the full mechanism is [`graphql-query-builder.md`](./graphql-query-builder.md)).
   3. The server **executes** that query against `storefront-graphql`. The
      aggregations are computed by the GraphQL resolver — deterministic, not
      LLM-estimated.
   4. The server **consolidates** the result into the typed `structured` payload
      and attaches `citations` and a `routing_decision`.
   → [`16-query-graphql-structured.request.json`](../examples/16-query-graphql-structured.request.json)
   / [`16-query-graphql-structured.response.json`](../examples/16-query-graphql-structured.response.json)

4. **action** — the same domain handles writes. *"Create a 10% discount code
   SUMMER10 for apparel…"* maps server-side to the `discountCreate` GraphQL
   mutation; the response records an `invoked` effect on `storefront-graphql`.
   → [`17-action-graphql.request.json`](../examples/17-action-graphql.request.json)
   / [`17-action-graphql.response.json`](../examples/17-action-graphql.response.json)

5. **explain** — the client inspects the routing for the query's `answer_id`
   (`ans-graphql-7a1f`): which domains were considered/queried, the rationale,
   per-source latency and confidence.
   → [`18-explain-graphql.request.json`](../examples/18-explain-graphql.request.json)
   / [`18-explain-graphql.response.json`](../examples/18-explain-graphql.response.json)

The client issued five primitive calls and received compiled, cited, typed
results. It never saw a line of GraphQL.

## REST and SQL backends

The same primitive mapping applies to any backend. A REST domain's `query`
builds an HTTP request (path + query params + filters) instead of a GraphQL
document and consolidates JSON responses; aggregations are computed by the
service or by the server after fetching. A SQL domain's `query` builds a
parameterized `SELECT ... GROUP BY` and the database computes the rollups. In
all three cases the rules are identical: the client sees only the seven
primitives, the backend is reached through a domain, aggregations are computed
deterministically server-side (never LLM-estimated), and the binding stays
private. Only the query-construction step differs — GraphQL document vs. HTTP
request vs. SQL statement.

Each backend has its own dedicated guide with mapping tables, a planner/builder
algorithm, an illustrative Python snippet, and a worked example:

- [`graphql-query-builder.md`](./graphql-query-builder.md) — GraphQL document
  (aggregation via the `aggregate` resolver). Worked thread: examples 14–18.
- [`rest-api-mapping.md`](./rest-api-mapping.md) — HTTP request sequence; REST
  has **no native aggregation**, so the server fetches rows and reduces them
  deterministically server-side. Worked thread: examples 19–22.
- [`sql-query-builder.md`](./sql-query-builder.md) — parameterized,
  injection-safe `SELECT ... GROUP BY`; SQL is the canonical
  deterministic-aggregation backend. Worked thread: examples 23–25.

## See also

- [`../SPEC.md`](../SPEC.md#relationship-to-mcp--lower-level-protocols) — Relationship to MCP (normative).
- [`graphql-query-builder.md`](./graphql-query-builder.md) — how step 3.2 actually works.
- [`intent-and-query-building.md`](./intent-and-query-building.md) — the prompts behind steps 3.1–3.2.
- [`../examples/`](../examples/) — the worked storefront files referenced above.
