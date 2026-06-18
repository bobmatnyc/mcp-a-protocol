---
Status: DRAFT
Owner: Robert Matsuoka
Date: 2026-06-18
Version: 1.0-beta
---

# MCP-A — MCP Answers Profile Specification (v1.0-beta)

## Abstract

MCP-A (MCP Answers Profile) is a specialization of the MCP protocol designed around three properties: **performance, precision, efficiency**.  It moves answer compilation and routing from the LLM-side to the server-side so the agent gets a faster, more precise answer while the expensive client-side model does less work.

Three things follow from that.  **Performance** -- a single compiled call instead of N tool calls the model has to orchestrate and stitch, which lowers end-to-end agent latency.  **Precision** -- typed, structured output with server-side **aggregations** (correct computed rollups, not LLM-estimated) and **disambiguation** (entity and term resolution server-side, not guessed), plus citations.  **Efficiency** -- a less expensive inference model classifies, structures, and compiles the response server-side, so the expensive client model consumes a finished result instead of doing the integration itself.

The spec defines six primitives -- **dynamic discovery**, **domain ontology/schema introspection**, **multi-source compiled answers**, **cheap multi-turn**, **personalized context**, and **routing explainability** -- plus a **structured-response mode** that returns typed objects conforming to a domain's published schema.  This specification establishes the behavior contract for conformant implementations.

## Scope

MCP-A defines:
- The core primitives (discover, schema, query, follow_up, context, explain) and their request/response shapes
- Domain ontology/schema introspection and a structured-response mode for `query` (typed, schema-conformant output)
- Error modes and conformance requirements (RFC 2119)
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
- **Disambiguation**: Server-side resolution of an ambiguous entity or term to a specific record or canonical value (e.g., "the Acme account" → a specific Salesforce Account ID) -- not guessed by the LLM.

## Three Pillars: Performance, Precision, Efficiency

Three properties define MCP-A.  They are the *why* -- the reason the primitives below take the shape they do.  The Design Principles that follow are the *how*.

- **Performance** -- MCP-A returns results *faster* than traditional MCP.  Server-side compilation plus fewer client round-trips means lower end-to-end latency for the agent: one compiled call instead of N tool calls the model has to orchestrate and stitch.  The model waits on one finished answer, not a chain of calls it has to sequence itself.

- **Precision** -- MCP-A ensures precision in what comes back.  **Aggregations** are correct server-side rollups, not LLM-estimated.  **Disambiguation** (entity and term resolution) happens server-side, not guessed by the model.  And the answer can come back as **structured, schema-conformant output** -- typed values against a domain's published ontology -- rather than prose approximations.  Structured + disambiguated + aggregated = precise.

- **Efficiency** -- MCP-A is cost-effective on the *server* side.  It uses a less expensive inference model to classify, structure, and compile the response, so the expensive client-side model does less work.  Cheap model structures; expensive model consumes a finished result.  This is the trade at the center of the spec: spend cheap server-side inference to save expensive client-side tokens and latency.

## Design Principles

1. **Compile Server-Side; Hand the LLM a Finished Result**: The core efficiency thesis. Routing, classification, multi-source consolidation, and RBAC filtering all happen server-side. The LLM receives a compiled answer with citations and metadata -- not N raw tool results to stitch.

2. **RBAC-Correct by Construction**: Every response respects the user's access scope. If a user cannot see a record, it never appears in an answer. Access scope is re-evaluated per-request, not cached.

3. **Dynamic Discovery Over Static Tool Defs**: Instead of a fixed list of available tools, `discover` returns a live catalog of information domains scoped to the user's permissions. Domains can be added, disabled, or filtered without redeploying clients.

4. **Compiled Answers Must Be Explainable**: Non-deterministic answers are only trustworthy if the caller can inspect *how* they were routed and *why*. `explain` is mandatory for production use.

5. **Cheap Multi-Turn**: Once an `answer_id` is issued, subsequent `follow_up` calls reuse the prior routing decision instead of re-classifying. Keeps cost low for natural conversation.

6. **Async-Friendly**: Long-running compiles (e.g., data warehouse aggregations) MUST be pollable via `*_chat_start`/`*_chat_poll` or equivalent. Clients must never block on compilation.

7. **Structured When Asked, Precise by Construction**: A caller MAY request a structured response against a schema. When it does, MCP-A returns typed objects -- with server-side aggregations and disambiguation already applied -- not prose the client has to parse. The cheap server-side model does the structuring; the client model consumes finished, typed values. This is the precision and efficiency pillars made concrete.

8. **Introspectable Domains**: A caller can ask what a domain's ontology is -- its entities, fields, types, relationships, and allowed aggregations -- before it queries. A domain is not an opaque box; its schema is discoverable so a client can request the right structured response and trust the shape it gets back.

## Primitives

### 1. discover

**Responsibility**: Return a dynamic, RBAC-filtered catalog of information domains available to the authenticated user.

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

#### Conformance Requirements

- MUST filter domains by user's access scope. If user has no access to a domain, it MUST NOT appear in the response.
- MUST support `semantic_filter` as optional substring/keyword match over domain names and descriptions.
- MUST return `freshness_seconds` for each domain so clients can decide whether to ask.
- MUST be cacheable by clients (suggest TTL of 5--60 minutes depending on how often domains change).
- SHOULD support pagination or `limit` for large catalogs.
- MAY mark domains as "deprecated" or "read-only" in an optional `status` field.

#### Error Modes

- `401 Unauthorized`: User not authenticated.
- `403 Forbidden`: User has no access to any domains (edge case).
- `400 Bad Request`: Invalid `semantic_filter` syntax (if pattern-based).

---

### 2. schema (domain introspection)

**Responsibility**: Return a domain's formal ontology/schema -- its entity types, fields, field types, relationships, units, and allowed aggregations -- so a caller knows what it can ask for and what shape a structured answer will take *before* it queries.

**Precision Rationale**: Structured, schema-conformant answers require the caller to know the schema. `schema` exposes the domain's ontology so a client can request the right `response_schema` on a `query` and trust the typed result it gets back.

schema is a first-class primitive -- the domain-introspection counterpart to discover. discover stays a thin catalog; schema carries the cacheable, versioned ontology surface.

#### Request

```json
{
  "user_id": "string (authenticated user ID)",
  "domain_id": "string (domain to introspect, e.g., 'salesforce-crm')",
  "include_aggregations": "boolean? (default true; include allowed aggregations per field)",
  "include_relationships": "boolean? (default true; include cross-entity relationships)"
}
```

#### Response

```json
{
  "domain_id": "string",
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

#### Conformance Requirements

- MUST return the ontology for a domain the user can access; MUST 403 (or omit) for domains outside the user's access scope.
- MUST list, per field, the aggregations the domain will compute server-side for that field, so a caller does not request an unsupported rollup.
- SHOULD return `schema_version` so a caller can detect when a domain's ontology changes.
- SHOULD be cacheable by clients (schemas change less often than data; suggest a longer TTL than `discover`).
- MAY omit relationships or aggregations if the caller sets the corresponding `include_*` flag false.

#### Error Modes

- `401 Unauthorized`: User not authenticated.
- `403 Forbidden`: User has no access to the requested domain.
- `404 Not Found`: `domain_id` does not exist.

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
    "draft": "boolean? (default false, if true, return draft answer without waiting for full compilation)"
  },
  "response_schema": "string | object? (optional structured-response target; bare string = registered shorthand, or a tagged {type} object; see Structured-Response Mode below)",
  "prose": "\"summary\" | \"full\" | \"none\"  (optional, default \"summary\")"
}
```

`response_schema` is an object with a `type` discriminator:
- `{ "type": "registered", "ref": "<name>" }` -- a schema registered in a known registry
- `{ "type": "domain", "domain_id": "<id>" }` -- target the named domain's published ontology
- `{ "type": "inline", "schema": { /* JSON Schema */ } }` -- a caller-supplied schema

A bare string is shorthand for the registered form: `"response_schema": "salesforce-crm"` is equivalent to `{ "type": "registered", "ref": "salesforce-crm" }`.

A server MUST reject an unknown `type`, or an unresolvable `ref`/`domain_id`, with `422` -- it MUST NOT guess.

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
  "is_draft": "boolean (true if options.draft was true and answer is incomplete)"
}
```

#### Conformance Requirements

- MUST classify the question against available domains and route to relevant source systems in parallel.
- MUST return citations with at least `source_system` and preferably a snippet or entity reference.
- MUST respect user's access scope: if a source system returns records the user cannot see, filter them out silently (no error).
- MUST return an `answer_id` so the answer can be referenced in `follow_up` and `explain` calls.
- MUST support `timeout_seconds` and return a best-effort draft if full compilation takes longer.
- MUST NOT cache the compiled answer across different users, even if the question is identical (answers are user-scoped).
- SHOULD include confidence if requested; MUST NOT return confidence >0.95 for answers fanned out to multiple sources without human review.
- MAY return `recommended_tool` to guide the user to drill deeper via a specific domain/tool.

#### Structured-Response Mode

When a caller supplies `response_schema`, `query` returns typed objects conforming to that schema in the `structured` field -- with citations -- instead of, or alongside, prose. This is the **Precision** pillar made concrete: the answer is disambiguated and aggregated server-side and handed back as typed values, not a prose approximation the client has to parse and re-derive. It is also the **Efficiency** pillar: the cheap server-side model does the structuring, so the expensive client model consumes a finished, typed result.

A caller learns a domain's schema via the `schema` primitive, then names it (or the domain) as the `response_schema` target.

Request sketch:

```json
{
  "question": "Total ARR by region for active accounts",
  "user_id": "u-123",
  "response_schema": { "type": "domain", "domain_id": "salesforce-crm" },
  "prose": "summary"
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

The optional request field `prose` controls the natural-language `answer` that accompanies a structured response:
- `"summary"` (default) -- a short paragraph alongside `structured`
- `"full"` -- the complete narrative answer
- `"none"` -- omit `answer`; return only typed objects

When `response_schema` is supplied, `structured` MUST be present and conformant (or `422`) and is the authoritative payload. `answer` is OPTIONAL and governed by `prose`. Pure-machine callers set `prose: "none"` to skip redundant tokens -- the Efficiency pillar.

Structured-mode conformance:

- When `response_schema` is supplied, MUST return `structured` conforming to that schema, or fail with `422` (see Error Modes) -- MUST NOT silently downgrade to prose-only without signaling.
- MUST apply server-side aggregations and disambiguation to produce typed values; aggregated fields MUST be computed, not LLM-estimated.
- MUST set `structured_schema_ref` to the schema/ontology the payload conforms to.
- MUST still return `citations` for structured payloads.
- An aggregation requested via the schema MUST be one the target domain declares as allowed in its `schema` response; otherwise fail with `400`.

#### Error Modes

- `400 Bad Request`: Question too vague or unparseable; or a requested aggregation is not allowed by the target domain's schema.
- `401 Unauthorized`: User not authenticated.
- `403 Forbidden`: User has no access to any domains that might answer the question.
- `408 Request Timeout`: Compilation did not complete within timeout (client may retry with longer timeout or poll via `follow_up`).
- `422 Unprocessable Entity`: `response_schema` was supplied but the compiled answer cannot be made to conform (e.g., the data does not fit the schema). MUST NOT silently fall back to prose-only.
- `503 Service Unavailable`: One or more source systems unreachable; return partial answer if possible, or fail cleanly.

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

Same shape as `query` response, but:
- `answer_id` may be the same (if refinement) or a new ID (if polling completed).
- `routing_decision` SHOULD indicate whether this was a re-route or reuse of prior routing.

#### Conformance Requirements

- MUST reuse the prior routing decision (same source systems, same domain classification) unless the refinement semantically requires a different routing.
- MUST NOT require re-authentication or re-RBAC-check per follow-up (RBAC was done in the prior `query`); however, if user's access scope has changed (e.g., record was shared away), the answer MUST reflect that.
- MUST support `drill_tool_id` to focus on a specific source system from the prior answer's `recommended_tool`.
- For long-running compiles: MUST support polling via repeated `follow_up` calls. Return a `status` field indicating "pending", "complete", etc.
- SHOULD keep the conversation cheap -- if a follow_up is a pure refinement (e.g., "narrow to Q3"), avoid re-fanning to all source systems; apply filtering post-hoc if possible.

#### Error Modes

- `400 Bad Request`: Invalid `answer_id` (expired or malformed).
- `404 Not Found`: `answer_id` not found or expired.
- `408 Request Timeout`: Polling or compilation still pending; client may retry.

---

### 5. context

**Responsibility**: Inspect or set user identity, preferences, memory, and access scope so future `query` calls return personalized, RBAC-correct answers.

**Efficiency Rationale**: Primes identity, preferences, and RBAC server-side so answers come back already personalized and access-correct. No extra round-trips to assemble context; it's baked in before the LLM sees the answer.

#### Request (Read)

```json
{
  "user_id": "string (authenticated user ID)",
  "include_preferences": "boolean? (default true)",
  "include_access_scope": "boolean? (default true)",
  "include_memory": "boolean? (default false)"
}
```

#### Request (Write)

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

- MUST return the authenticated user's current identity and access scope.
- MUST return preferences so clients can adjust output formatting, language, etc.
- MUST allow clients to update preferences without affecting other users.
- Memory (recent domains, prior answers) is OPTIONAL but RECOMMENDED for multi-turn UX.
- Access scope MUST be re-evaluated on every `context` read (not cached); it is the source of truth for RBAC.
- MUST NOT leak access scope of other users.

#### Error Modes

- `401 Unauthorized`: User not authenticated.
- `400 Bad Request`: Invalid preference or memory key.

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

- `400 Bad Request`: Invalid `answer_id`.
- `404 Not Found`: `answer_id` not found or expired.

---

## Access Scope & RBAC Model

Every primitive that returns user-scoped data (discover, query, context, explain) MUST:

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

Implementations MAY declare one of the following conformance levels:

- **Core**: Implements `query` + `context`. Sufficient for single-turn, personalized prose answers.
- **Full**: Implements `discover`, `schema`, `query` (including structured-response mode), `follow_up`, `context`, and `explain` -- the full primitive set plus domain ontology/schema introspection and schema-conformant structured query. Recommended for production systems.
- **Extended**: Full + vendor-specific extensions (e.g., custom drill tools, feedback models).

Domain introspection (`schema`) and structured-response mode are part of **Full** conformance, not Core -- a Core implementation may return prose only.

Clients SHOULD query `discover` to determine what primitives are available, and `schema` to determine a domain's ontology, before relying on structured-response mode.

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

**Key principle**: Every MCP-A server is a conformant MCP server. MCP-A defines specific tools (the six primitives) and result shapes on top of MCP's base contract. Every MCP-A endpoint is an MCP endpoint; MCP-A adds semantic constraints around discovery, routing, and answer compilation.

How they work together:

- **MCP tools** (e.g., `read_file`, `search_docs`) are *source systems* that MCP-A can fan out to.
- **MCP-A discover** might return domains like "codebase-search", which are backed by MCP tools.
- **MCP-A query** might route to the "codebase-search" domain, which internally calls MCP tools and consolidates results.
- **MCP-A explain** reveals which underlying MCP tools were queried and why.

In other words, MCP-A wraps and orchestrates deterministic tool-calling to provide dynamic, personalized, explainable compiled answers. It trades server-side MCP tool orchestration for LLM-side token and latency savings.

---

## Security & RBAC Model (Detailed)

### Authentication

All six primitives MUST require authentication. Recommended mechanisms:
- JWT bearer tokens.
- API keys with user context.
- OAuth 2.0 with OIDC.

### Authorization (Per-Primitive)

- **discover**: Filter domains by user's roles/teams. Return only domains the user can access.
- **query**: Filter source systems and results by user's access scope. If a source system returns a record the user cannot see, remove it from citations without error.
- **follow_up**: Inherit RBAC from the prior query. If user's access scope changed since the prior query, re-evaluate and return updated answer (or error if access was revoked).
- **context**: Return only the authenticated user's own context. Do NOT return another user's context.
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

5. **Structured Queries (input side)**: This spec adds structured *output* (response_schema → typed objects). Structured *input* -- a query DSL (e.g., SQL-like filters over JIRA issues) in addition to NL -- is still open. Future extensions may add an optional `structured_query` request field.

6. **Domain Versioning**: If a domain's schema changes (e.g., new fields in SFDC), how do we version it? The `schema` primitive returns a `schema_version`, but the policy for evolving an ontology without breaking callers (deprecation windows, additive-only rules) is not yet specified.

---

## References

- [duetto-intelligence MCP Gateway](../../../services/duetto-intelligence/) (current Duetto implementation, partial)
- [POSITIONING.md](./POSITIONING.md) (landscape analysis)
- [RFC-PROCESS.md](./RFC-PROCESS.md) (governance, MAEP process)
- [DI-GAP-ANALYSIS.md](./DI-GAP-ANALYSIS.md) (implementation roadmap)
- RFC 2119: Keywords for use in Internet Drafts and RFCs (MUST, SHOULD, MAY, etc.)
