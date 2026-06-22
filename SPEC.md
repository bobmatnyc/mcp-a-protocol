---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-18
---

# MCP-A — MCP Answers Profile Specification (v1.0-beta)

## Abstract

MCP-A (MCP Answers Profile) is a specialization of the MCP protocol designed around three properties: **performance, precision, efficiency**. It moves answer compilation and routing from the LLM-side to the server-side so the agent gets a faster, more precise answer while the expensive client-side model does less work.

Three things follow from that. **Performance** -- a single compiled call instead of N tool calls the model has to orchestrate and stitch, which lowers end-to-end agent latency. **Precision** -- typed, structured output with server-side **aggregations** (correct computed rollups, not LLM-estimated) and **disambiguation** (entity and term resolution server-side, not guessed), plus citations. **Efficiency** -- a less expensive inference model classifies, structures, and compiles the response server-side, so the expensive client model consumes a finished result instead of doing the integration itself.

The spec defines **seven** answer primitives -- **dynamic discovery**, **domain ontology/schema introspection**, **multi-source compiled answers**, **state-changing actions**, **cheap multi-turn**, **personalized context**, and **routing explainability** -- plus a **structured-response mode** that returns typed objects conforming to a domain's published schema. This specification establishes the behavior contract for conformant implementations.

## Scope

MCP-A defines:
- The seven core primitives (discover, schema, query, action, follow_up, context, explain) and their request/response shapes
- Domain ontology/schema introspection via the dedicated `schema` primitive, and a structured-response mode for `query` (typed, schema-conformant output)
- An abstract error taxonomy with canonical transport mappings (see §Error Model)
- Conformance requirements (RFC 2119)
- RBAC and access-scope model
- Relationship to MCP: MCP-A is an MCP profile/specialization; every MCP-A server IS a conformant MCP server
- Versioning and extension model

MCP-A does **not** specify:
- Transport bindings (HTTP, gRPC, MCP transport, etc.) -- those are implementation details
- Specific source systems or their APIs -- MCP-A remains source-agnostic
- Machine-learning routing or compilation algorithms
- Specific authentication/authorization mechanisms (only the contract)

## Terminology

- **Information Domain**: A bounded, discoverable scope of knowledge -- e.g., "Salesforce CRM", "JIRA Issues", "Internal Contracts". Owned by one or more source systems. Has freshness, access scope, example questions.
- **Compiled Answer**: A response assembled by classifying intent, fanning out across multiple potential sources, and consolidating into a single authoritative answer with citations. Non-deterministic -- the routing/sources may vary for the same question given context or state changes.
- **Answer ID** (`answer_id`): A handle (opaque string) that identifies a compiled answer for multi-turn follow-ups and polling.
- **Routing**: The process of classifying a question, determining which source systems to query, and how to merge their responses.
- **Fan-Out**: Parallel querying of multiple source systems for a single question.
- **Drill Path** (`recommended_tool`): A reference to a specific downstream tool or system that can provide deeper/narrower results on a related question.
- **Access Scope**: The set of resources (documents, records, entities) a user is authorized to see. RBAC-evaluated per-request, not per-session.
- **Freshness**: The age of data in a domain; MUST be returned by discover and queryable by clients.
- **Ontology / Schema**: A domain's formal description -- its entity types, fields, field types, relationships, units, and allowed aggregations. Introspectable so a caller knows what it can ask for and what shape the answer takes before it queries.
- **Structured Response**: A `query` result returned as typed objects conforming to a named or domain-published schema, plus citations -- instead of, or alongside, prose.
- **Aggregation**: A computed rollup (count, sum, average, min/max, group-by, etc.) produced server-side from source data, returned as a typed value. Correct by computation, not estimated by the model.
- **Disambiguation**: Server-side resolution of an ambiguous entity or term to a specific record or canonical value -- not guessed by the LLM.
- **Conformance Level**: One of Core, Full, or Extended -- see §Conformance Levels.
- **Action ID** (`action_id`): A handle (opaque string) that identifies a state-changing action across clarification rounds and for `explain`. Stable from the first response until the action completes or expires.
- **Clarification**: The reactive mechanism by which an `action` reports the information it still needs (`clarification.needed[]`) before it can execute. The client supplies those fields in a continuation request's `inputs` map. The proactive counterpart is `schema(target: action)` -- see §action and §2.
- **Effect** (`ActionEffect`): A single state change an `action` applied at a source system (e.g., a record created, an email sent). Reported in the `effects` array of a completed action.
- **Schema target** (`target`): For the `schema` primitive, what to introspect -- `domain` (default), `query`, or `action`. With `target: action`, `schema` enumerates a domain's available actions or returns a single action's input schema.
- **Schema path / drill** (`path`, `depth`, `truncated`, `expandable`, `max_depth`): The hierarchical-introspection controls on `schema`. `path` (dotted) addresses a node to drill into and `depth` bounds how far to expand; the response echoes `path`, marks `truncated` when deeper levels exist, lists `expandable` node paths the client may drill into next, and reports `max_depth` available from the addressed node.

## Three Pillars: Performance, Precision, Efficiency

Three properties define MCP-A. They are the *why* -- the reason the primitives below take the shape they do. The Design Principles that follow are the *how*.

- **Performance** -- MCP-A returns results *faster* than traditional MCP. Server-side compilation plus fewer client round-trips means lower end-to-end latency for the agent: one compiled call instead of N tool calls the model has to orchestrate and stitch. The model waits on one finished answer, not a chain of calls it has to sequence itself.

- **Precision** -- MCP-A ensures precision in what comes back. **Aggregations** are correct server-side rollups, not LLM-estimated. **Disambiguation** (entity and term resolution) happens server-side, not guessed by the model. And the answer can come back as **structured, schema-conformant output** -- typed values against a domain's published ontology -- rather than prose approximations. Structured + disambiguated + aggregated = precise.

- **Efficiency** -- MCP-A is cost-effective on the *server* side. It uses a less expensive inference model to classify, structure, and compile the response, so the expensive client-side model does less work. Cheap model structures; expensive model consumes a finished result. This is the trade at the center of the spec: spend cheap server-side inference to save expensive client-side tokens and latency.

## Design Principles

1. **Compile Server-Side; Hand the LLM a Finished Result**: The core efficiency thesis. Routing, classification, multi-source consolidation, and RBAC filtering all happen server-side. The LLM receives a compiled answer with citations and metadata -- not N raw tool results to stitch.

2. **RBAC-Correct by Construction**: Every response respects the user's access scope. If a user cannot see a record, it never appears in an answer. Access scope is re-evaluated per-request, not cached.

3. **Dynamic Discovery Over Static Tool Defs**: Instead of a fixed list of available tools, `discover` returns a live catalog of information domains scoped to the user's permissions. Domains can be added, disabled, or filtered without redeploying clients.

4. **Compiled Answers Must Be Explainable**: Non-deterministic answers are only trustworthy if the caller can inspect *how* they were routed and *why*. `explain` is mandatory for production use.

5. **Cheap Multi-Turn**: Once an `answer_id` is issued, subsequent `follow_up` calls reuse the prior routing decision instead of re-classifying. Keeps cost low for natural conversation.

6. **Async-Friendly**: Long-running compiles (e.g., data warehouse aggregations) MUST be pollable via `follow_up`. Clients must never block on compilation.

7. **Structured When Asked, Precise by Construction**: A caller MAY request a structured response against a schema. When it does, MCP-A returns typed objects -- with server-side aggregations and disambiguation already applied -- not prose the client has to parse. The cheap server-side model does the structuring; the client model consumes finished, typed values. This is the precision and efficiency pillars made concrete.

8. **Introspectable Domains**: A caller can ask what a domain's ontology is -- its entities, fields, types, relationships, and allowed aggregations -- before it queries. A domain is not an opaque box; its schema is discoverable so a client can request the right structured response and trust the shape it gets back.

## Error Model

MCP-A defines an **abstract error taxonomy** independent of transport. Because MCP-A does not mandate a transport binding (HTTP, gRPC, MCP JSON-RPC, etc.), error codes are defined as named abstract codes. Each primitive's Error Modes references these abstract codes. Implementers MUST map them to the transport's native error encoding.

### Abstract Error Codes

| Code | Meaning |
|------|---------|
| `UNAUTHENTICATED` | The caller did not supply valid credentials. |
| `FORBIDDEN` | The caller is authenticated but lacks permission for the requested resource or domain. |
| `INVALID_REQUEST` | The request is malformed, missing required fields, or violates a protocol constraint. |
| `DOMAIN_NOT_FOUND` | The requested `domain_id` does not exist in the server's registry. |
| `ANSWER_NOT_FOUND` | The referenced `answer_id` does not exist or has expired. |
| `SCHEMA_NONCONFORMANT` | A structured response was requested (`response_schema` supplied) but the compiled answer cannot be made to conform to the target schema. |
| `AGGREGATION_NOT_ALLOWED` | A requested aggregation is not in the domain's declared `allowed_aggregations`. |
| `TIMEOUT` | The request did not complete within the specified or default timeout. |
| `SOURCE_UNAVAILABLE` | One or more upstream source systems are unreachable. Implementations SHOULD return a partial answer when possible. |
| `ACTION_NOT_FOUND` | The referenced `action_id` does not exist or has expired (`action` primitive). |
| `ACTION_FAILED` | An `action` was interpreted and authorized but execution failed at the source system. |

### Canonical Transport Mappings

Implementations MUST communicate errors using their transport's native encoding. The following canonical mappings are RECOMMENDED.

| Abstract Code | HTTP Status | MCP / JSON-RPC Code |
|---------------|-------------|---------------------|
| `UNAUTHENTICATED` | 401 | -32001 |
| `FORBIDDEN` | 403 | -32002 |
| `INVALID_REQUEST` | 400 | -32600 |
| `DOMAIN_NOT_FOUND` | 404 | -32003 |
| `ANSWER_NOT_FOUND` | 404 | -32004 |
| `SCHEMA_NONCONFORMANT` | 422 | -32005 |
| `AGGREGATION_NOT_ALLOWED` | 400 | -32006 |
| `TIMEOUT` | 408 | -32007 |
| `SOURCE_UNAVAILABLE` | 503 | -32008 |
| `ACTION_NOT_FOUND` | 404 | -32009 |
| `ACTION_FAILED` | 502 | -32010 |

> NORMATIVE (v1.0-beta): The JSON-RPC error code values above (`-32001` … `-32010`) sit in the `-32000`–`-32099` range the JSON-RPC 2.0 specification reserves for implementation-defined server errors. These specific values are **normative for v1.0-beta**: a conformant JSON-RPC binding MUST use exactly these numeric codes for the corresponding abstract codes. The assignment is recorded in CHANGELOG.md and is revisable only through the MAEP process. (Clients still SHOULD branch on the abstract code name, not the numeric value — see the note below.) `ACTION_NOT_FOUND`/`ACTION_FAILED` were added by MAEP-0003.

Implementations MAY include additional context (e.g., which domain triggered `FORBIDDEN`, or which source triggered `SOURCE_UNAVAILABLE`) in an error detail payload alongside the abstract code. Clients MUST NOT rely on transport-specific numeric codes for logic -- they SHOULD inspect the abstract code name from the error payload when available.

---

## Primitives

### 1. discover

**Responsibility**: Return a dynamic, RBAC-filtered catalog of information domains available to the authenticated user, plus server capability metadata.

**Efficiency Rationale**: Replaces static tool definitions sent on every request. The LLM no longer carries a massive static tool catalog in context; it asks what's available, scoped to the user. Smaller context, dynamic scope updates without redeployment.

#### Request

```json
{
  "user_id": "string (authenticated user ID)",
  "semantic_filter": "string? (optional natural-language filter, e.g., 'contracts')",
  "limit": "integer? (default 100)"
}
```

#### Response

```json
{
  "server": {
    "mcp_a_version": "string (e.g., '1.0-beta')",
    "conformance_level": "string ('Core' | 'Full' | 'Extended')",
    "supported_primitives": ["string", "... (e.g., ['discover','schema','query','action','follow_up','context','explain'])"]
  },
  "domains": [
    {
      "id": "string (stable domain identifier, e.g., 'salesforce-crm')",
      "name": "string",
      "description": "string (what questions can this domain answer?)",
      "example_questions": ["string", "..."],
      "source_systems": ["string", "... (names of underlying systems)"],
      "freshness_seconds": "integer (how old is the data?)",
      "access_scope": "string (e.g., 'user-scoped', 'team-scoped', 'org-scoped')",
      "requires_context_fields": ["string?", "... (e.g., ['account_id'] if domain is per-account)"]
    },
    "..."
  ],
  "total_count": "integer",
  "timestamp": "RFC3339 timestamp of discovery time"
}
```

The `server` block MUST be present in every `discover` response. It advertises the server's MCP-A version, conformance level, and which primitives are available. Clients SHOULD use this block -- rather than probing individual primitives -- to determine server capabilities before relying on structured-response mode or other Full/Extended features.

> RESOLVED (beta): The `server` capability block is included in the `discover` response (not as a separate endpoint) to keep capability negotiation to a single round-trip. The `supported_primitives` array lists exactly which primitives this server exposes; if a primitive is absent, clients MUST NOT call it.

#### Conformance Requirements

- MUST filter domains by user's access scope. If user has no access to a domain, it MUST NOT appear in the response.
- MUST include the `server` block with `mcp_a_version`, `conformance_level`, and `supported_primitives` in every response.
- `conformance_level` MUST accurately reflect what the server implements per §Conformance Levels. A server MUST NOT declare `Full` unless all seven primitives are implemented.
- MUST support `semantic_filter` as optional substring/keyword match over domain names and descriptions.
- MUST return `freshness_seconds` for each domain so clients can decide whether to ask.
- MUST be cacheable by clients (suggest TTL of 5--60 minutes depending on how often domains change).
- SHOULD support pagination or `limit` for large catalogs.
- MAY mark domains as "deprecated" or "read-only" in an optional `status` field.

#### Error Modes

- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `FORBIDDEN`: User has no access to any domains (edge case). (HTTP 403)
- `INVALID_REQUEST`: Invalid `semantic_filter` syntax (if pattern-based). (HTTP 400)

---

### 2. schema

**Responsibility**: Return a domain's formal ontology/schema -- its entity types, fields, field types, relationships, units, and allowed aggregations -- so a caller knows what it can ask for and what shape a structured answer will take *before* it queries.

**Precision Rationale**: Structured, schema-conformant answers require the caller to know the schema. `schema` exposes the domain's ontology so a client can request the right `response_schema` on a `query` and trust the typed result it gets back.

`schema` is a first-class primitive -- the domain-introspection counterpart to `discover`; `discover` stays a thin catalog, `schema` carries the cacheable, versioned ontology surface.

#### Request

```json
{
  "user_id": "string (authenticated user ID)",
  "domain_id": "string (domain to introspect; required when target is 'domain'/absent)",
  "target": "string? ('domain' | 'query' | 'action'; default 'domain') (MAEP-0004)",
  "action_id": "string? (only with target 'action': present => that action's input schema; absent => enumerate actions) (MAEP-0004)",
  "path": "string? (dotted node path to drill into, e.g. 'order.line_items') (MAEP-0004)",
  "depth": "integer? (>=1, default 2; levels to expand) (MAEP-0004)",
  "include_aggregations": "boolean? (default true; include allowed aggregations per field)",
  "include_relationships": "boolean? (default true; include cross-entity relationships)"
}
```

#### Response

```json
{
  "domain_id": "string",
  "target": "string? (echo of request target; absent => 'domain') (MAEP-0004)",
  "path": "string? (echo of the node this response describes; absent => root) (MAEP-0004)",
  "truncated": "boolean? (deeper levels exist beyond returned depth) (MAEP-0004)",
  "expandable": ["string?", "... (node paths the client may drill into) (MAEP-0004)"],
  "max_depth": "integer? (total depth available from the addressed node) (MAEP-0004)",
  "actions": ["string?", "... (available action names; with target 'action', no action_id) (MAEP-0004)"],
  "action_input_schema": "object? (inline JSON Schema for one action's inputs; with target 'action' + action_id) (MAEP-0004)",
  "schema_version": "string (the domain's own schema version; see Open Questions on domain versioning)",
  "entities": [
    {
      "type": "string (entity type, e.g., 'Account')",
      "description": "string?",
      "fields": [
        {
          "name": "string (e.g., 'arr')",
          "type": "string (scalar/enum/date/reference/etc.)",
          "unit": "string? (e.g., 'USD', 'days')",
          "nullable": "boolean?",
          "allowed_aggregations": ["string", "... (e.g., 'sum', 'avg', 'count', 'min', 'max')"],
          "enum_values": ["string?", "... (if type is enum)"]
        },
        "..."
      ],
      "relationships": [
        {
          "name": "string (e.g., 'opportunities')",
          "target_entity": "string (e.g., 'Opportunity')",
          "cardinality": "string (one-to-one, one-to-many, many-to-many)"
        },
        "..."
      ]
    },
    "..."
  ],
  "timestamp": "RFC3339 timestamp"
}
```

**Field stability.** The field names in this spec (`allowed_aggregations`, `cardinality`, `schema_version`, etc.) are normative for v1.0-beta. Minor renames may still occur before 1.0 stable; any such change is recorded in CHANGELOG.md and goes through the MAEP process. From 1.0 stable onward, field-level changes follow the versioning policy — a breaking rename is a major-version bump.

#### Hierarchical drilling and operation introspection (MAEP-0004)

`schema` accepts OPTIONAL hierarchical and operation-aware controls. All are additive: a request supplying only `user_id` + `domain_id` behaves exactly as defined above.

- **`target`** (`domain` | `query` | `action`, default `domain`) — what to introspect. Absent ⇒ `domain` (the ontology behavior described above).
- **`path`** (dotted string, e.g. `order.line_items`) — a node to drill into. Absent ⇒ the root.
- **`depth`** (integer ≥ 1, default 2) — levels to expand from the addressed node.
- **`action_id`** — only meaningful with `target: action`. Present ⇒ return that action's input schema; absent ⇒ enumerate available actions.

The response echoes `target` and `path`, and for a drilled domain ontology adds:

- **`truncated`** (boolean) — deeper levels exist beyond the returned `depth`.
- **`expandable`** (string[]) — node paths the client MAY drill into via a subsequent `path`.
- **`max_depth`** (integer) — total depth available from the addressed node.

For `target: action`, the response carries **`actions`** (string[], the available action names) when no `action_id` was supplied, and an inline JSON Schema describing a single action's `inputs` when an `action_id` was supplied.

Request sketch (drill):

```json
{ "user_id": "u-123", "domain_id": "commerce-orders", "path": "order.line_items", "depth": 1 }
```

Request sketch (operation introspection):

```json
{ "user_id": "u-123", "domain_id": "salesforce-crm", "target": "action", "action_id": "create_task" }
```

This is the **proactive** counterpart to the `action` primitive's **reactive** `clarification` rounds (§7, MAEP-0003): a client MAY fetch an action's input schema up front and supply complete inputs on its first `action` call, avoiding a clarification round-trip.

#### Conformance Requirements

- MUST return the ontology for a domain the user can access; MUST return `FORBIDDEN` for domains outside the user's access scope.
- MUST list, per field, only the aggregations the domain will compute server-side for that field (deterministically, not LLM-estimated); see §Aggregation Correctness Conformance. A caller can request only these listed aggregations without ambiguity.
- MUST treat a request with only `user_id` + `domain_id` (no `target`/`path`/`depth`) exactly as the pre-MAEP-0004 ontology behavior — these controls are additive.
- When a returned node's subtree was not fully expanded within `depth`, MUST set `truncated: true` and populate `expandable` with the drillable node paths; when fully expanded, MUST report `truncated: false`. Every `expandable` entry MUST be a valid `path` for a subsequent request.
- With `target: action`: MUST return `actions` (RBAC-filtered to actions the user may invoke) when no `action_id` is supplied, and MUST return the named action's input schema when `action_id` is supplied. MUST return `ACTION_NOT_FOUND` for an unknown `action_id`.
- SHOULD return `schema_version` so a caller can detect when a domain's ontology changes.
- SHOULD be cacheable by clients (schemas change less often than data; suggest a longer TTL than `discover`); a drilled response is cacheable per `(domain_id, target, path, depth)`.
- MAY omit relationships or aggregations if the caller sets the corresponding `include_*` flag false.

#### Error Modes

- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `FORBIDDEN`: User has no access to the requested domain. (HTTP 403)
- `DOMAIN_NOT_FOUND`: `domain_id` does not exist. (HTTP 404)
- `ACTION_NOT_FOUND`: `target: action` was requested with an `action_id` that does not exist. (HTTP 404)

---

### 3. query

**Responsibility**: Answer a natural-language question by classifying intent, fanning out to relevant source systems, consolidating results, and returning a source-cited compiled answer.

**Efficiency Rationale**: Server classifies once, fans out in parallel, consolidates one answer. The LLM consumes one finished answer with citations instead of orchestrating N tool calls and stitching raw outputs. Fewer round-trips, less re-reasoning per turn.

#### Request

```json
{
  "question": "string (natural-language question)",
  "user_id": "string (authenticated user ID)",
  "context": {
    "account_id": "string? (if multi-tenant)",
    "user_preferences": "object? (e.g., timezone, output format)",
    "prior_answers": ["answer_id?", "... (optional, for context-aware refinement)"]
  },
  "options": {
    "timeout_seconds": "integer? (default 30)",
    "include_confidence": "boolean? (default false)",
    "draft": "boolean? (default false, if true, return draft answer without waiting for full compilation)",
    "include_prose": "boolean? (default true, controls whether prose answer summary is included alongside structured output)"
  },
  "response_schema": "object? (optional structured-response target with explicit discriminator; see Structured-Response Mode below)"
}
```

> RESOLVED (beta): `response_schema` uses an explicit tagged discriminator to disambiguate the target:
>
> ```json
> "response_schema": {
>   "kind": "schema_ref" | "domain" | "inline",
>   "value": "string (schema name) | string (domain_id) | object (inline schema definition)"
> }
> ```
>
> This eliminates string ambiguity and is extensible to future kinds. Clients MUST inspect `kind` to interpret `value`.

#### Response

```json
{
  "answer": "string (the compiled, natural-language answer; MAY be omitted or summary-only when structured output is returned)",
  "structured": "object | array? (typed objects conforming to the requested response_schema; present only when response_schema was supplied)",
  "structured_schema_ref": "string? (which schema/ontology the structured payload conforms to)",
  "answer_id": "string (opaque handle for follow_up calls)",
  "citations": [
    {
      "source_system": "string (e.g., 'salesforce-crm')",
      "domain_id": "string (e.g., 'salesforce-crm')",
      "entity_type": "string? (e.g., 'Account', 'Opportunity')",
      "entity_id": "string? (e.g., a record ID)",
      "snippet": "string? (the relevant quote from the source)",
      "confidence": "number? (0.0--1.0, if requested)"
    },
    "..."
  ],
  "recommended_tool": {
    "id": "string (tool/domain ID for drilling deeper)",
    "reason": "string (why this tool might provide more detail)"
  },
  "routing_decision": "object? (only if debug/explain requested; see explain primitive)",
  "timestamp": "RFC3339 timestamp when answer was compiled",
  "is_draft": "boolean? (OPTIONAL; absent ⇒ false. true only on a draft/partial answer; see is_draft note below)"
}
```

> `is_draft` is **OPTIONAL** on the `query` response. When absent, it defaults to `false` — i.e., a normal, complete answer. A server returns `is_draft: true` **only** on a draft/partial answer (i.e., when the request set `options.draft: true` and compilation has not finished); see §Async & Polling Model. `is_draft` is therefore NOT a required field (it is excluded from the schema's `required` set for `query.response`), so a complete answer MAY omit it entirely. Clients MUST treat a missing `is_draft` as `false`.

#### Conformance Requirements

- MUST classify the question against available domains and route to relevant source systems in parallel.
- MUST return citations with at least `source_system` and preferably a snippet or entity reference.
- MUST respect user's access scope: if a source system returns records the user cannot see, filter them out silently (no error).
- MUST return an `answer_id` so the answer can be referenced in `follow_up` and `explain` calls.
- MUST support `timeout_seconds` and return a best-effort draft if full compilation takes longer.
- `is_draft` is OPTIONAL and defaults to `false` when absent: a normal, complete answer MAY omit it, and clients MUST treat its absence as `false`. A server MUST set `is_draft: true` only on a draft/partial answer (see §Async & Polling Model); it MUST NOT set `is_draft: true` on a complete answer.
- MUST NOT cache the compiled answer across different users, even if the question is identical (answers are user-scoped).
- SHOULD include confidence if requested; MUST NOT return confidence >0.95 for answers fanned out to multiple sources without human review.
- MAY return `recommended_tool` to guide the user to drill deeper via a specific domain/tool.

#### Structured-Response Mode

When a caller supplies `response_schema`, `query` returns typed objects conforming to that schema in the `structured` field -- with citations -- instead of, or alongside, prose. This is the **Precision** pillar made concrete: the answer is disambiguated and aggregated server-side and handed back as typed values, not a prose approximation the client has to parse and re-derive. It is also the **Efficiency** pillar: the cheap server-side model does the structuring, so the expensive client model consumes a finished, typed result.

A caller learns a domain's schema via the `schema` primitive, then targets it via a tagged `response_schema` object.

Request sketch:

```json
{
  "question": "Total ARR by region for active accounts",
  "user_id": "u-123",
  "response_schema": {
    "kind": "domain",
    "value": "salesforce-crm"
  },
  "options": {
    "include_prose": true
  }
}
```

Response sketch:

```json
{
  "structured": [
    { "region": "AMER", "active_accounts": 412, "total_arr": 18250000, "currency": "USD" },
    { "region": "EMEA", "active_accounts": 287, "total_arr": 9930000, "currency": "USD" }
  ],
  "structured_schema_ref": "salesforce-crm",
  "answer": "AMER leads on ARR; full breakdown in the structured payload.",
  "answer_id": "ans-9f2",
  "citations": [ { "source_system": "salesforce-crm", "domain_id": "salesforce-crm" } ],
  "timestamp": "2026-06-18T00:00:00Z"
}
```

> RESOLVED (beta): When `response_schema` is supplied, `query` returns the prose `answer` as an OPTIONAL short summary (present when `include_prose=true`), with `structured` as the authoritative payload. The caller controls whether to receive prose via `options.include_prose` (default `true`).

Structured-mode conformance:

- When `response_schema` is supplied with explicit `kind` discriminator, MUST return `structured` conforming to that schema, or fail with `SCHEMA_NONCONFORMANT` -- MUST NOT silently downgrade to prose-only without signaling.
- MUST apply server-side aggregations and disambiguation to produce typed values; aggregated fields MUST be computed, not LLM-estimated. See §Aggregation Correctness Conformance below.
- MUST set `structured_schema_ref` to the schema/ontology the payload conforms to.
- MUST still return `citations` for structured payloads.
- When `include_prose=true`, return a short prose `answer` summary; when `include_prose=false`, `answer` MAY be omitted or null.
- An aggregation requested via the schema MUST be one the target domain declares as allowed in its `schema` response; otherwise fail with `AGGREGATION_NOT_ALLOWED`.

#### Error Modes

- `INVALID_REQUEST`: Question too vague or unparseable; or a requested aggregation is not allowed by the target domain's schema. (HTTP 400)
- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `FORBIDDEN`: User has no access to any domains that might answer the question. (HTTP 403)
- `TIMEOUT`: Compilation did not complete within timeout (client may retry with longer timeout or poll via `follow_up`). (HTTP 408)
- `SCHEMA_NONCONFORMANT`: `response_schema` was supplied but the compiled answer cannot be made to conform. MUST NOT silently fall back to prose-only. (HTTP 422)
- `SOURCE_UNAVAILABLE`: One or more source systems unreachable; return partial answer if possible, or fail cleanly. (HTTP 503)

---

### 4. follow_up

**Responsibility**: Refine or drill a prior answer, or poll a long-running compilation. Keeps multi-turn conversations efficient by reusing the prior routing decision.

**Efficiency Rationale**: Drills and polls against an answer_id with no re-classification. The expensive routing happens once; follow-ups are cheap. Multi-turn stays efficient instead of re-routing/re-classifying on every message.

#### Request

```json
{
  "answer_id": "string (from a prior query response)",
  "refinement": "string? (natural-language refinement, e.g., 'focus on Q3 only')",
  "drill_tool_id": "string? (specific tool ID to drill into, from recommended_tool)",
  "user_id": "string (authenticated user ID)",
  "options": {
    "timeout_seconds": "integer? (default 30)",
    "poll_interval_ms": "integer? (hint for polling, default 1000)"
  }
}
```

#### Response

Same shape as the `query` response (see §3), with one additional field for polling:

```json
{
  "...": "all query-response fields (answer, structured, answer_id, citations, recommended_tool, routing_decision, timestamp, is_draft)",
  "status": "string? (enum: 'pending' | 'complete'). 'pending' = still compiling (poll again); 'complete' = compilation done. SHOULD be present, and MUST be present for long-running/polled compiles."
}
```

and with these semantics:
- `answer_id` may be the same (if refinement) or a new ID (if polling completed).
- `routing_decision` SHOULD indicate whether this was a re-route or reuse of prior routing.
- `status` reports compilation progress for polling: `pending` means the compile is still running and the response carries the cached draft (`is_draft: true`); `complete` means compilation finished and the response carries the final answer (`is_draft: false`). The field is OPTIONAL on the wire (it is not in the schema's `required` set) but MUST be present on any response to a poll of a long-running compile, per the conformance requirement below and §Async & Polling Model.

#### Conformance Requirements

- MUST reuse the prior routing decision (same source systems, same domain classification) unless the refinement semantically requires a different routing.
- MUST NOT require re-authentication per follow-up; however, RBAC MUST be re-evaluated per §RBAC Authorization per Primitive. If user's access scope has changed (e.g., a record was shared away) since the prior `query`, the answer MUST reflect the current scope.
- MUST support `drill_tool_id` to focus on a specific source system from the prior answer's `recommended_tool`.
- For long-running compiles: MUST support polling via repeated `follow_up` calls. Return a `status` field indicating "pending", "complete", etc.
- SHOULD keep the conversation cheap -- if a follow_up is a pure refinement (e.g., "narrow to Q3"), avoid re-fanning to all source systems; apply filtering post-hoc if possible.

#### Error Modes

- `INVALID_REQUEST`: Invalid `answer_id` (malformed). (HTTP 400)
- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `ANSWER_NOT_FOUND`: `answer_id` not found or expired. (HTTP 404)
- `TIMEOUT`: Polling or compilation still pending; client may retry. (HTTP 408)

---

### 5. context

**Responsibility**: Inspect or set user identity, preferences, memory, and access scope so future `query` calls return personalized, RBAC-correct answers.

**Efficiency Rationale**: Primes identity, preferences, and RBAC server-side so answers come back already personalized and access-correct. No extra round-trips to assemble context; it's baked in before the LLM sees the answer.

A `context` request comes in two shapes — **Read** and **Write** — distinguished by a single explicit discriminator: the presence of the `action` field. A **Write** request is identified by the presence of `action` (one of `set` / `append` / `clear`); a **Read** request MUST omit `action`. There is no separate `mode` tag — `action` is the discriminator, exactly as the `context.request` schema encodes it (`oneOf` Read vs. Write, keyed on whether `action` is present). A request that supplies `action` is validated and handled as a Write; one that omits it is a Read. Servers MUST reject a request that is ambiguous under this rule (e.g., a Write body missing `action`) with `INVALID_REQUEST`.

> A future refinement MAY introduce an explicit `mode` tag (`"mode": "read" | "write"`) for self-documentation; for v1.0-beta the presence/absence of `action` is the normative discriminator and no `mode` field is defined.

#### Request (Read)

A Read request omits `action`.

```json
{
  "user_id": "string (authenticated user ID)",
  "include_preferences": "boolean? (default true)",
  "include_access_scope": "boolean? (default true)",
  "include_memory": "boolean? (default false)"
}
```

#### Request (Write)

A Write request is identified by the presence of `action`.

```json
{
  "user_id": "string (authenticated user ID)",
  "action": "set" | "append" | "clear",
  "preferences": {
    "timezone": "string?",
    "output_format": "string? (json, markdown, plain-text)",
    "language": "string?",
    "..."
  },
  "memory": {
    "key": "value or null (for clearing)"
  }
}
```

#### Response

```json
{
  "user_id": "string",
  "preferences": {
    "timezone": "string",
    "output_format": "string",
    "language": "string",
    "..."
  },
  "access_scope": {
    "teams": ["string", "..."],
    "accounts": ["string", "..."],
    "roles": ["string", "..."],
    "resource_tags": ["string", "..."],
    "..."
  },
  "memory": {
    "recent_domains": ["string", "... (domains queried recently)"],
    "recent_answers": ["answer_id", "..."],
    "preferences_last_updated": "RFC3339 timestamp"
  },
  "timestamp": "RFC3339 timestamp"
}
```

#### Conformance Requirements

- MUST discriminate Read vs. Write requests by the presence of the `action` field: a request carrying `action` (`set`/`append`/`clear`) is a Write; a request omitting `action` is a Read. Servers MUST reject an ambiguous or malformed request under this rule with `INVALID_REQUEST`.
- MUST return the authenticated user's current identity and access scope.
- MUST return preferences so clients can adjust output formatting, language, etc.
- MUST allow clients to update preferences without affecting other users.
- Memory (recent domains, prior answers) is OPTIONAL but RECOMMENDED for multi-turn UX.
- Access scope MUST be re-evaluated on every `context` read (not cached); it is the source of truth for RBAC.
- MUST NOT leak access scope of other users.

#### Error Modes

- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `INVALID_REQUEST`: Invalid preference or memory key. (HTTP 400)

---

### 6. explain

**Responsibility**: Inspect how a compiled answer was routed, why it routed that way, and inspect/provide feedback to improve future routing.

**Efficiency Rationale**: Exposes routing decisions, sources, and confidence so the LLM (or user) can trust a compiled, non-deterministic answer without re-deriving it from scratch. Verification without recomputation.

#### Request

```json
{
  "answer_id": "string (from a prior query response)",
  "user_id": "string (authenticated user ID)",
  "include_latency": "boolean? (default true)",
  "include_confidence": "boolean? (default true)",
  "feedback": {
    "helpful": "boolean?",
    "comments": "string?",
    "expected_sources": ["string?", "... (sources the user thought should have been queried)"]
  }
}
```

#### Response

```json
{
  "answer_id": "string",
  "question_classified_as": "string (how the system understood the question)",
  "domains_considered": ["string", "..."],
  "domains_queried": ["string", "..."],
  "routing_decision": {
    "algorithm": "string? (e.g., 'semantic-match', 'user-history', 'heuristic')",
    "rationale": "string (why these domains were chosen)",
    "alternative_routings": [
      {
        "domains": ["string", "..."],
        "score": "number (relative confidence 0.0--1.0)",
        "reason": "string"
      }
    ]
  },
  "source_latencies": {
    "domain_id": "integer (milliseconds to compile)"
  },
  "confidence_per_source": {
    "domain_id": "number (0.0--1.0)"
  },
  "feedback_recorded": "boolean (if feedback was provided)"
}
```

#### Conformance Requirements

- MUST provide a human-readable explanation of the routing decision.
- MUST include alternative routings that were considered but not chosen, with their scores.
- MUST return per-source latencies and confidences so clients can judge answer quality.
- MUST accept and record feedback (helpful/not, expected sources) to improve future routing.
- MUST NOT share feedback from other users in the explain response.
- Feedback SHOULD be anonymized before being used to train routing models.

#### Error Modes

- `INVALID_REQUEST`: Invalid `answer_id` (malformed). (HTTP 400)
- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `ANSWER_NOT_FOUND`: `answer_id` not found or expired. (HTTP 404)

---

### 7. action

**Responsibility**: Take a **state-changing** action on the user's behalf from a natural-language request. The service interprets the request with a tool-using model and either executes immediately and reports what it did, or — if it lacks needed information — returns what it still needs and waits for the client to supply it. `action` is the write-side counterpart to `query` (added by MAEP-0003).

**Efficiency Rationale**: Server interprets the intent, resolves the entities, and performs the change in one compiled call — the expensive client model expresses *what* to do in natural language and consumes a typed account of *what was done*, instead of orchestrating and stitching the write itself. There is **no mandatory confirm or dry-run step**; safe by RBAC and (when needed) by clarification.

`action` is a **Full** primitive; the Core tier stays read-only (`query` + `context`). RBAC MUST be re-evaluated on every `action` call and checked **before** any effect is applied.

#### Request

An `action` request has two shapes, discriminated by the presence of `action_id` (mirroring `context`'s Read/Write `oneOf`).

A **New action** (MUST omit `action_id`):

```json
{
  "request": "string (natural-language state-changing request)",
  "user_id": "string (authenticated user ID)",
  "context": {
    "account_id": "string? (if multi-tenant)",
    "user_preferences": "object? (e.g., timezone, output format)"
  },
  "options": {
    "timeout_seconds": "integer? (>=1, default 30)",
    "include_confidence": "boolean?"
  }
}
```

A **Continuation** (MUST include `action_id` + `inputs`, MUST omit `request`):

```json
{
  "action_id": "string (from a prior clarification_required response)",
  "user_id": "string (authenticated user ID)",
  "inputs": { "<field from clarification.needed[].name>": "value", "...": "..." }
}
```

#### Response

```json
{
  "action_id": "string (stable across clarification rounds; usable with explain)",
  "status": "string (enum: 'clarification_required' | 'completed' | 'failed')",
  "summary": "string? (human-readable account of what was done / what is needed)",
  "clarification": {
    "needed": [
      {
        "name": "string (key the client supplies in the continuation `inputs`)",
        "description": "string?",
        "type": "string? (string|number|integer|boolean|object|array)",
        "required": "boolean?",
        "example": "any?",
        "enum": ["any?", "..."]
      }
    ],
    "prompt": "string?"
  },
  "result": "object | array | string | null (outcome payload, when completed)",
  "effects": [
    {
      "kind": "string (created|updated|deleted|sent|invoked|other)",
      "resource": "string (e.g., 'Task', 'email')",
      "source_system": "string (e.g., 'salesforce')",
      "entity_id": "string?",
      "detail": "object?"
    }
  ],
  "citations": [ { "source_system": "string", "...": "... (see §3)" } ],
  "error": "object? (present only when status is 'failed'; shaped per error.json)",
  "routing_decision": "object? (only if debug/explain requested)",
  "timestamp": "RFC3339 timestamp?"
}
```

#### Conformance Requirements

- MUST interpret the natural-language `request` server-side and either execute the change or return `clarification_required` with the fields it needs; MUST NOT silently guess missing required inputs.
- MUST return `action_id` and `status` on every response. `clarification` MUST be present when and only when `status` is `clarification_required`; `error` MUST be present when and only when `status` is `failed`.
- MUST keep `action_id` stable across clarification rounds and resolvable by `explain`.
- MUST re-evaluate RBAC on every call and verify the user's scope **before** applying any effect; on denial, return `FORBIDDEN` and apply no effect.
- MUST report the state changes it applied in `effects` when `status` is `completed`, each with at least `kind`, `resource`, and `source_system`.
- MUST NOT apply any effect when returning an error.
- The fields an action needs are discoverable **proactively** via `schema(target: action, action_id: …)` (see §2, MAEP-0004) and **reactively** via these `clarification` rounds (MAEP-0003). A Full server exposing `action` MUST support the reactive path and SHOULD support the proactive path.
- There is no mandatory confirmation step; a deployment that wants one MAY model it as a required `clarification` field (e.g., a `confirm` boolean).

#### Error Modes

- `INVALID_REQUEST`: Unparseable request, or a continuation whose `inputs` do not satisfy the requested `clarification.needed`. (HTTP 400)
- `UNAUTHENTICATED`: User not authenticated. (HTTP 401)
- `FORBIDDEN`: User lacks permission for the requested action (RBAC denial). (HTTP 403)
- `ACTION_NOT_FOUND`: `action_id` unknown or expired. (HTTP 404)
- `TIMEOUT`: Interpretation/execution did not complete within timeout. (HTTP 408)
- `ACTION_FAILED`: Execution failed at the source system. (HTTP 502)

> Section numbering: `action` is appended as §7 to keep the existing §4–§6 (`follow_up`, `context`, `explain`) anchors and cross-references stable. Conceptually it is the write-side counterpart to `query` (§3).

---

## Aggregation Correctness Conformance

To uphold the **Precision** pillar ("correct rollups, not LLM-estimated"), the following conformance requirement is mandatory:

- A domain MUST NOT advertise (in `allowed_aggregations` within the `schema` response) or return any aggregation that was estimated, derived, or produced by an LLM.
- All advertised aggregations MUST be computed deterministically server-side via database queries, GraphQL resolvers, or direct computation over source data (not via learned model inference).
- If a domain cannot compute an aggregation deterministically, it MUST NOT list it as allowed in `allowed_aggregations`.
- This ensures that when a caller requests a `query` with `response_schema` and server-side aggregation, the `structured` result is guaranteed to be precise (computed, not estimated), not a model approximation.

This conformance requirement is the enforcement mechanism for the Precision pillar and is auditable: `schema` queries MUST NOT return an aggregation that the domain did not compute deterministically for the given result.

---

## Access Scope & RBAC Model

Every primitive that returns user-scoped data MUST enforce RBAC. The following table summarizes per-primitive authorization rules.

### RBAC Authorization per Primitive

| Primitive | Authorization Rule |
|-----------|-------------------|
| **discover** | Filter domains by user's roles/teams. MUST NOT return domains the user cannot access. |
| **schema** | MUST return `FORBIDDEN` for any `domain_id` outside the user's access scope. Filter or deny domains the user cannot query. |
| **query** | Filter source systems and results by user's access scope. Remove inaccessible records silently, without error. |
| **action** | Write path: RBAC re-evaluated per call and the user's scope checked **before** any effect is applied. Deny with `FORBIDDEN` and apply no effect if the user lacks permission. Never inherited or cached. |
| **follow_up** | Inherit RBAC from the prior query's `answer_id`. MUST re-evaluate access scope at follow-up time: if user's permissions changed since the prior query, the answer MUST reflect the current scope (or return `FORBIDDEN` if access was revoked). |
| **context** | Return only the authenticated user's own context and access scope. MUST NOT return another user's context. |
| **explain** | Return routing decisions for the user's own answers only (matched by `answer_id` + `user_id`). |

### General RBAC Requirements

Every primitive that returns user-scoped data MUST:

1. **Authenticate** the user (verify identity).
2. **Evaluate RBAC** (fetch user's roles, team memberships, resource tags).
3. **Filter Results** (silently exclude any domain, record, or citation the user cannot access).
4. **Re-evaluate Per-Request** (RBAC is not cached across requests; if a user's permissions change mid-session, the next request reflects it).

**Access Scope Dimensions** (examples; implementations may vary):
- **Team/Org**: User is member of Team A, can see Team A's domains.
- **Account** (multi-tenant): User is admin of Account B, can see Account B's resources.
- **Role**: User is "analyst", can query domains tagged "analyst-allowed".
- **Resource Tags**: User can see resources tagged with any of their assigned tags.

**Confidentiality Guarantee**: If user A queries a domain, the answer MUST NOT leak any information about resources user A cannot access. Implementations MUST use row-level security, view-based filtering, or equivalent.

---

## Async & Polling Model

For long-running compilations (e.g., data warehouse queries, aggregations):

1. **Call `query`** with `options.draft = true`.
2. Server returns a partial answer + `is_draft: true` + `answer_id`.
3. **Poll via `follow_up`** with the same `answer_id`.
4. Server returns either:
   - Still pending (return cached draft + `is_draft: true`).
   - Complete (return final answer + `is_draft: false` + updated citations).

Alternatively, implementations MAY support webhooks or server-sent events for async callbacks.

---

## Conformance Levels

Implementations MUST declare one of the following conformance levels in the `server` block of `discover` responses:

- **Core**: Implements `query` + `context`. Sufficient for single-turn, personalized prose answers. The Core tier is **read-only**. A Core server MUST declare `supported_primitives` listing at minimum `["query", "context"]`.
- **Full**: Implements all **seven** primitives: `discover`, `schema`, `query` (including structured-response mode), `action`, `follow_up`, `context`, and `explain` -- plus domain ontology/schema introspection (including hierarchical drilling and operation introspection per §2/MAEP-0004) and schema-conformant structured query. Recommended for production systems. A Full server MUST declare all seven in `supported_primitives`.
- **Extended**: Full + vendor-specific extensions (e.g., custom drill tools, feedback models). A server MUST NOT declare Extended unless it satisfies all Full requirements.

Domain introspection (`schema`, including drilling/operation introspection), structured-response mode, and the state-changing `action` primitive are part of **Full** conformance, not Core -- a Core implementation is read-only and may return prose only.

Clients SHOULD call `discover` to read the `server.supported_primitives` list before calling any primitive, and call `schema` to learn a domain's ontology before relying on structured-response mode.

---

## Versioning & Extension

- **Semantic versioning**: Major.Minor.Patch (e.g., 1.0.0).
- **Major bump** when a primitive's response shape changes in a breaking way.
- **Minor bump** when a new optional field is added to a request or response.
- **Patch bump** for bug fixes and clarifications.

**Extensions**: Vendors MAY add new fields to responses (marked as optional) without bumping the major version. Clients SHOULD ignore unknown fields.

---

## Relationship to MCP & Lower-Level Protocols

MCP-A is a **profile** (semantic layer) of MCP. It does not replace MCP; it specializes it.

**Key principle**: Every MCP-A server is a conformant MCP server. MCP-A defines specific tools (the **seven primitives**: discover, schema, query, action, follow_up, context, explain) and result shapes on top of MCP's base contract. Every MCP-A endpoint is an MCP endpoint; MCP-A adds semantic constraints around discovery, routing, and answer compilation.

How they work together:

- **MCP tools** (e.g., `read_file`, `search_docs`) are *source systems* that MCP-A can fan out to.
- **MCP-A discover** might return domains like "codebase-search", which are backed by MCP tools.
- **MCP-A query** might route to the "codebase-search" domain, which internally calls MCP tools and consolidates results.
- **MCP-A explain** reveals which underlying MCP tools were queried and why.

In other words, MCP-A wraps and orchestrates deterministic tool-calling to provide dynamic, personalized, explainable compiled answers. It trades server-side MCP tool orchestration for LLM-side token and latency savings.

---

## Security & RBAC Model (Detailed)

### Authentication

All seven primitives MUST require authentication. Recommended mechanisms:
- JWT bearer tokens.
- API keys with user context.
- OAuth 2.0 with OIDC.

### Authorization (Per-Primitive)

See §RBAC Authorization per Primitive above for the full table. Summary:

- **discover**: Filter domains by user's roles/teams. Return only domains the user can access.
- **schema**: MUST return `FORBIDDEN` for domains outside the user's access scope.
- **query**: Filter source systems and results by user's access scope. Remove inaccessible records silently.
- **action**: Re-evaluate RBAC per call; check scope before applying any effect. Deny with `FORBIDDEN` and apply no effect if unauthorized.
- **follow_up**: Inherit prior-answer RBAC; re-evaluate access scope at follow-up time. If scope changed, return updated answer or `FORBIDDEN` if access was revoked.
- **context**: Return only the authenticated user's own context.
- **explain**: Return routing decisions for the user's own answers only.

### Audit Logging

Implementations SHOULD log:
- Query text (may be sensitive; consider retention policy).
- Which domains were queried.
- User ID and their access scope at query time.
- Final answer delivered.
- Feedback provided by the user.

---

## Open Questions & Future Work

1. **Caching**: Should compiled answers be cached? For how long? This spec does not mandate caching, but implementations may cache for the same user + same question within a short window (e.g., 5 minutes). Clients SHOULD assume answers are not cached.

2. **Feedback Loops**: How should routing models improve from user feedback? This spec captures the feedback signal but does not mandate a specific ML approach. Future MAEP (MCP-A Enhancement Proposal) may standardize feedback integration.

3. **Confidence Scoring**: What is the definition of confidence? Precision, recall, or agreement across sources? This spec mentions confidence but does not define the algorithm. Future MAEP may standardize scoring.

4. **Multi-Language Support**: Should domains, questions, and answers support i18n? This spec mentions `language` in preferences but does not specify locale handling.

5. **Structured Queries (input side)**: This spec adds structured *output* (response_schema → typed objects). Structured *input* -- a query DSL (e.g., SQL-like filters over a domain) in addition to NL -- is still open. Future extensions may add an optional `structured_query` request field.

6. **Domain Versioning**: If a domain's schema changes (e.g., new fields), how do we version it? The `schema` primitive returns a `schema_version`, but the policy for evolving an ontology without breaking callers (deprecation windows, additive-only rules) is not yet specified.

7. **Error Code Registry**: The JSON-RPC error code values in the canonical transport mapping table (§Error Model) are **locked as normative for v1.0-beta** (recorded in CHANGELOG.md). Any future change to these numeric assignments goes through the MAEP process.

---

## References

- [POSITIONING.md](./POSITIONING.md) (landscape analysis)
- [RFC-PROCESS.md](./RFC-PROCESS.md) (governance, MAEP process)
- [MAEP/0001-structured-responses-and-introspection.md](./MAEP/0001-structured-responses-and-introspection.md) (MAEP-0001: `schema` primitive and structured-response mode)
- [MAEP/0002-session-management.md](./MAEP/0002-session-management.md) (MAEP-0002, Draft: session management hook + Full-tier capability)
- [MAEP/0003-action-primitive.md](./MAEP/0003-action-primitive.md) (MAEP-0003, Draft: the `action` primitive — write-side counterpart to `query`)
- [MAEP/0004-hierarchical-schema.md](./MAEP/0004-hierarchical-schema.md) (MAEP-0004, Draft: hierarchical + operation-aware `schema` introspection)
- RFC 2119: Keywords for use in Internet Drafts and RFCs (MUST, SHOULD, MAY, etc.)
