---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-18
---

# Quickstart — Build Your First MCP-A Server

This guide takes you from "I already have an MCP server" to a conformant MCP-A server, in the
order you should build it: **`discover` capability block → `query` (prose) for Core → add
`schema` + structured mode for Full**. It is transport-agnostic — MCP-A defines behavior and
shapes, not bindings (SPEC §Scope). Code against the JSON Schemas in
[`schemas/`](./schemas/); they are the contracts. Run the worked example in
[`examples/`](./examples/) alongside this guide.

## Prerequisites

- An MCP server you already operate. **Every MCP-A server is a conformant MCP server** (SPEC
  §Relationship to MCP) — MCP-A adds six named tools (the primitives) and their result shapes
  on top of MCP's base contract. You are adding tools, not replacing your server.
- One or more backing source systems you can query and aggregate over (a database, a
  warehouse, GraphQL resolvers, existing MCP tools). These become your **information domains**.
- The schemas in [`schemas/`](./schemas/) (JSON Schema draft 2020-12). Validate your real
  request/response payloads against them in tests.

## Mental model

MCP-A moves answer compilation server-side. Instead of handing the LLM a static tool catalog
and raw results to stitch, you expose a small set of primitives that return *compiled*
answers. The primitives map onto your source systems like this:

- A **domain** is a bounded, queryable slice of your data (e.g., `salesforce-crm`).
- `discover` advertises which domains a user may see.
- `schema` describes a domain's ontology so callers can request typed output.
- `query` classifies a question, fans out to the domain's source systems, and consolidates.
- `follow_up` / `explain` / `context` make multi-turn cheap, trustworthy, and personalized.

---

## Step 1 — Expose the `server` capability block via `discover`

Start by telling clients what you are. Add a `discover` tool that returns the **`server`
block** plus an RBAC-filtered domain catalog. The `server` block MUST be present on every
`discover` response (SPEC §1).

Contract: [`schemas/discover.request.json`](./schemas/discover.request.json) /
[`schemas/discover.response.json`](./schemas/discover.response.json).
Example: [`examples/01-discover.*`](./examples/).

Minimum viable response:

```json
{
  "server": {
    "mcp_a_version": "1.0-beta",
    "conformance_level": "Core",
    "supported_primitives": ["query", "context"]
  },
  "domains": [
    {
      "id": "salesforce-crm",
      "name": "Salesforce CRM",
      "description": "Accounts, opportunities, and pipeline.",
      "freshness_seconds": 900
    }
  ]
}
```

Implementation checklist:

- Authenticate the caller (`user_id`); MCP-A requires auth on all primitives (SPEC §Security).
- Filter `domains` by the user's access scope — never return a domain the user can't see
  (SPEC §1, §RBAC).
- Return `freshness_seconds` per domain (SPEC §1).
- Set `conformance_level` honestly. Declare what you actually implement — you will bump it to
  `Full` after Step 3 (SPEC §1, §Conformance Levels).
- Support the optional `semantic_filter` and `limit` (SPEC §1).

> A Core server still benefits from `discover`: even at Core you can return the `server` block
> so clients negotiate capabilities in one round-trip. Just keep `supported_primitives`
> accurate — clients MUST NOT call a primitive that isn't listed.

## Step 2 — Implement `query` (prose) — this is Core

The compiled answer is the heart of MCP-A. For **Core** conformance you need `query` + `context`
returning single-turn personalized prose (SPEC §Conformance Levels).

Contract: [`schemas/query.request.json`](./schemas/query.request.json) /
[`schemas/query.response.json`](./schemas/query.response.json).
Example: [`examples/03-query-prose.*`](./examples/).

Inside `query`, do the work the LLM used to do:

1. **Classify** the natural-language `question` against your available domains.
2. **Fan out** to the relevant source systems in parallel.
3. **Consolidate** into one answer.
4. **Cite** your sources — every citation MUST carry at least `source_system` (SPEC §3).
5. **Issue an `answer_id`** — an opaque handle clients reuse in `follow_up`/`explain`. Persist
   the routing decision and result against it.

Required response fields (per schema): `answer_id`, `citations`, `is_draft`.

Hard rules (SPEC §3):

- Respect access scope — silently drop records the user can't see (no error).
- **Never** cache a compiled answer across different users, even for an identical question.
- Support `options.timeout_seconds`; on overrun, return a best-effort draft (`is_draft: true`)
  or `TIMEOUT`.
- If you report confidence, don't exceed 0.95 for multi-source fan-out without human review.

Also implement `context` (SPEC §5, [`schemas/context.*`](./schemas/)) so answers are
personalized and RBAC-correct: return the user's identity, preferences, and access scope, and
allow preference writes. Re-evaluate access scope on every read — it is your RBAC source of
truth, never cached.

**At this point you are Core-conformant.** Declare
`"conformance_level": "Core"`, `"supported_primitives": ["query", "context"]` (plus
`discover` if you exposed it).

## Step 3 — Add `schema` + structured mode for Full

To reach **Full**, implement all six primitives plus ontology introspection and
structured-response mode (SPEC §Conformance Levels).

### 3a. `schema` — publish each domain's ontology

Contract: [`schemas/schema.request.json`](./schemas/schema.request.json) /
[`schemas/schema.response.json`](./schemas/schema.response.json).
Example: [`examples/02-schema.*`](./examples/).

For each domain, return its `entities`, their `fields` (name, type, unit, nullability),
`relationships`, and — per field — `allowed_aggregations`. Return `FORBIDDEN` for domains
outside the user's scope (SPEC §2).

**Critical:** `allowed_aggregations` is a promise. List only aggregations you compute
**deterministically** server-side (SQL, warehouse query, GraphQL resolver) — never anything an
LLM estimates (SPEC §Aggregation Correctness). If you can't compute `sum` for a field
deterministically, don't list `sum`.

### 3b. Structured-response mode on `query`

When a caller supplies `response_schema`, return typed objects in `structured` instead of (or
alongside) prose. The target uses a tagged discriminator (SPEC §3, RESOLVED beta):

```json
"response_schema": { "kind": "domain", "value": "salesforce-crm" }
```

`kind` is one of `schema_ref` (a named schema), `domain` (a domain's published ontology), or
`inline` (an inline schema object). Inspect `kind` to interpret `value`.

Example: [`examples/04-query-structured.*`](./examples/). Rules (SPEC §3):

- Return `structured` conforming to the target, **or** fail with `SCHEMA_NONCONFORMANT` — never
  silently fall back to prose-only.
- Apply server-side aggregation and disambiguation; aggregated values MUST be computed.
- Set `structured_schema_ref` to the conforming schema/ontology.
- Still return `citations`.
- Honor `options.include_prose`: when `true`, include a short prose `answer` summary; when
  `false`, `answer` MAY be null/omitted.
- A requested aggregation MUST be in the target field's `allowed_aggregations`; otherwise fail
  with `AGGREGATION_NOT_ALLOWED` (see [`examples/07-error-aggregation.*`](./examples/)).

### 3c. `follow_up` and `explain`

- **`follow_up`** ([`schemas/follow_up.*`](./schemas/), [`examples/05-follow_up.*`](./examples/)):
  refine/drill against an `answer_id` reusing the prior routing — don't re-classify for a pure
  narrowing. Re-evaluate RBAC at follow-up time. Support polling with a `status` field
  (`pending`/`complete`) for long-running compiles (SPEC §4).
- **`explain`** ([`schemas/explain.*`](./schemas/), [`examples/06-explain.*`](./examples/)):
  return the routing decision with `alternative_routings` and scores, per-source latencies and
  confidences, and record `feedback` (SPEC §6).

**Now declare Full:**

```json
"server": {
  "mcp_a_version": "1.0-beta",
  "conformance_level": "Full",
  "supported_primitives": ["discover", "schema", "query", "follow_up", "context", "explain"]
}
```

## Step 4 — Errors

Use the abstract error taxonomy (SPEC §Error Model). Errors are shaped per
[`schemas/error.json`](./schemas/error.json): a named `code`, a `message`, and optional
`detail`. Map the abstract code to your transport's native encoding (HTTP status / JSON-RPC
code) per the canonical table; clients branch on the abstract `code` name, not the numeric
value. See [`examples/07-error-aggregation.response.json`](./examples/) for a real
`AGGREGATION_NOT_ALLOWED` payload.

## Verify against the schemas

Validate your real payloads against [`schemas/`](./schemas/) in your test suite. See
[`examples/README.md`](./examples/README.md#validating-these-examples) for a ready-to-run
Python (`jsonschema` + `referencing`) and Node (`ajv-cli`) harness with cross-file `$ref`
resolution. Then walk your implementation through the same seven-step scenario in
[`examples/`](./examples/) and diff your output against the example responses.

## Where to go next

- [`CONFORMANCE.md`](./CONFORMANCE.md) — the full self-audit checklist for your declared level.
- [`SPEC.md`](./SPEC.md) — the normative behavior contract.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — propose changes via the MAEP process.
