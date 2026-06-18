---
MAEP: 0001
Title: Initial MCP-A Primitive Set
Author: Robert Matsuoka <bob@matsuoka.com>
Status: Accepted
Date: 2026-06-18
Spec-Version: 1.0-beta
---

## Summary

MAEP-0001 formalizes the foundational primitive set for MCP-A v1.0-beta: `discover`, `schema`, `query` (including structured-response mode), `follow_up`, `context`, and `explain`.

## Motivation

MCP-A is designed to move answer compilation from the LLM to the server, enabling **performance**, **precision**, and **efficiency**. To achieve this, a minimal but complete set of primitives is necessary:

- **Dynamic Discovery** (`discover`): Replaces static tool definitions with a live, RBAC-filtered catalog of information domains.
- **Schema Introspection** (`schema`): Exposes a domain's ontology so callers can request structured, typed responses.
- **Compiled Answers** (`query`): Classifies intent, fans out to source systems, and returns a single consolidated answer with citations.
- **Cheap Multi-Turn** (`follow_up`): Drills/refines against a prior answer without re-classification.
- **Personalized Context** (`context`): Primes identity, preferences, memory, and RBAC so answers come back already personalized.
- **Routing Explainability** (`explain`): Exposes how and why an answer was compiled so callers can trust non-deterministic results.

Together, these six elements (five answer primitives + domain ontology introspection) constitute the minimal sufficient set for the v1.0-beta specification.

## Proposed Solution

### The Six Elements

#### 1. `discover` — Dynamic Domain Catalog
- Returns a live, RBAC-filtered list of information domains.
- Replaces static tool definitions, reducing context bloat and enabling dynamic permission changes.
- Supports optional semantic filtering.
- See SPEC.md §1.

#### 2. `schema` — Domain Introspection
- Returns a domain's formal ontology: entity types, fields, field types, relationships, units, and allowed aggregations.
- Enables **Precision Pillar**: callers know what structure to expect before querying.
- Kept as a dedicated primitive (not folded into `discover`) because schemas have a different cache TTL and versioning lifecycle than the domain catalog.
- See SPEC.md §2.

#### 3. `query` — Compiled Answer
- The core primitive. Accepts a natural-language question, classifies it, fans out to relevant source systems in parallel, and returns one consolidated answer.
- Returns citations, confidence (optional), and a `recommended_tool` for drilling deeper.
- Supports **structured-response mode**: when a caller supplies a `response_schema` (with explicit tagged discriminator), returns typed objects conforming to the domain's schema instead of prose.
- Structured answers include server-side aggregations and disambiguation, enforcing **Precision**.
- See SPEC.md §3.

#### 4. `follow_up` — Cheap Multi-Turn
- Refines or drills a prior answer by reusing the routing decision from the prior `query`.
- Also polls long-running compilations (async pattern).
- Keeps multi-turn efficient: routing happens once, follow-ups are cheap.
- See SPEC.md §4.

#### 5. `context` — Personalized Identity & RBAC
- Reads/writes user identity, preferences, memory, and access scope.
- Primes server-side state so subsequent queries return personalized and RBAC-correct answers.
- See SPEC.md §5.

#### 6. `explain` — Routing Explainability
- Inspects how a compiled answer was routed, which domains were queried, and why.
- Returns alternative routings that were considered.
- Accepts user feedback (helpful/not, expected sources) to improve future routing.
- Mandatory for production use of compiled answers.
- See SPEC.md §6.

### Key Design Decisions Resolved in Beta

#### Design Decision 1: `schema` as Dedicated Primitive
**Resolved**: `schema` is kept separate from `discover` because:
- Schemas change far less frequently than domain catalogs (different cache TTL).
- Schemas carry their own `schema_version` lifecycle.
- Keeping `schema` separate preserves `discover` as a thin catalog and `schema` as deep introspection.
- This separation is foundational to the Precision pillar: callers must know the schema before requesting structured responses.

*Reference*: SPEC.md §2 "RESOLVED (beta):" block.

#### Design Decision 2: `response_schema` Uses Tagged Discriminator
**Resolved**: `response_schema` is no longer a bare `string | object`. It is now:
```json
{
  "kind": "schema_ref" | "domain" | "inline",
  "value": "string (schema name) | string (domain_id) | object (inline schema definition)"
}
```

**Rationale**:
- Both a schema name and a domain_id are strings; bare duck-typing creates ambiguity.
- An explicit `kind` tag removes ambiguity and is extensible to future target kinds.
- Clients MUST inspect `kind` before interpreting `value`.

*Reference*: SPEC.md §3 query request, Structured-Response Mode sketches.

#### Design Decision 3: Prose Alongside Structured is Caller-Controlled
**Resolved**: Added `options.include_prose` (default `true`):
- When structured output is returned: prose `answer` is an OPTIONAL short summary (present when `include_prose=true`).
- `structured` is always the authoritative payload.
- Callers can suppress prose entirely if they prefer only typed objects.

*Reference*: SPEC.md §3 query options, Structured-Response Mode conformance.

#### Design Decision 4: Aggregation Correctness Conformance
**Resolved**: Added mandatory conformance requirement:
- A domain MUST NOT advertise or return any aggregation that was LLM-estimated.
- All advertised aggregations MUST be computed deterministically server-side (DB/GQL/compute path).
- If a domain cannot compute an aggregation deterministically, it MUST NOT list it as allowed.

**Rationale**:
- This is the enforcement mechanism for the Precision pillar ("correct rollups, not LLM-estimated").
- Ensures that when a caller requests a structured query with aggregation, the result is guaranteed precise, not model-estimated.
- Auditable: `schema` queries MUST NOT return an aggregation that the domain did not compute deterministically for the given result.

*Reference*: SPEC.md §Aggregation Correctness Conformance (new section), and schema §Conformance Requirements.

## Rationale

### Why Six Elements, Not Five?

The spec describes "five answer primitives" (`discover`, `query`, `follow_up`, `context`, `explain`), but early discussions conflated domain ontology introspection with these primitives. MAEP-0001 clarifies: **`schema` is a sixth element alongside the five answer primitives**, not folded into any of them. Together, they form the complete minimal set for v1.0-beta.

This is not a recount; it's a clarification. The spec has always treated `schema` as a core element (§2 is substantive); MAEP-0001 formalizes its independence and resolves the ambiguity.

### Why These Design Decisions?

1. **`schema` Dedicated**: Schemas have different freshness and versioning semantics than domain catalogs. Separating them keeps both surfaces clean and cacheable.

2. **Tagged Discriminator for `response_schema`**: String ambiguity in a distributed protocol is a bug waiting to happen. An explicit tag prevents misinterpretation and future-proofs the protocol.

3. **Caller-Controlled Prose**: Different clients have different needs. Some want both prose and structure; others prefer only typed objects. Defaulting to both (with a toggle) maximizes flexibility.

4. **Aggregation Correctness**: The Precision pillar is meaningless if aggregations can be LLM-estimated. This conformance requirement makes the promise auditable and enforceable.

## Backwards Compatibility

MAEP-0001 is accepted as part of v1.0-beta. Because v1.0-beta is pre-release, these resolutions do not trigger a major version bump; they are incorporated into the stable v1.0.0 release.

**Implementation Guidance**:
- Implementers building v1.0-beta reference implementations MUST include all four resolutions.
- Clients querying a v1.0-beta server can assume `response_schema` is tagged, `schema` is a dedicated primitive, and aggregations are deterministic.

## Implementation Notes

### For Implementers

1. **`schema` Introspection**:
   - Cache schema responses with a longer TTL than `discover` (suggest 1 hour+ vs. 5-15 minutes for `discover`).
   - Increment `schema_version` whenever a field, relationship, or allowed aggregation changes.

2. **Tagged `response_schema`**:
   - Parse the `kind` field first. Clients MUST reject responses with unknown `kind` values.
   - Document the three kinds clearly: `schema_ref` (named schema), `domain` (domain ontology), `inline` (schema as JSON).

3. **Aggregation Computation**:
   - Do not return aggregations via LLM post-processing. Compute all aggregations (count, sum, avg, min, max, group-by, etc.) in your database or query layer.
   - Update `allowed_aggregations` in the `schema` response ONLY for aggregations the domain computes deterministically.
   - Audit regularly: spot-check that returned aggregations match the declared `allowed_aggregations`.

4. **`include_prose` Default Behavior**:
   - Default `include_prose=true` for backwards compatibility (clients that don't specify get both).
   - When `include_prose=false`, `answer` MAY be omitted entirely or set to `null`.
   - Ensure `structured` is always present and complete when `response_schema` was supplied (never downgrade to prose-only without error).

### Open Questions Remaining (for Future MAEPs)

The following are documented in SPEC.md §Open Questions as still open:

1. **Caching Policy**: Should compiled answers be cached? For how long? (Feedback-dependent.)
2. **Confidence Definition**: Precision, recall, or cross-source agreement? (Standardization opportunity.)
3. **Feedback ML Integration**: How should routing models improve from user feedback? (Algorithm-specific; future MAEP.)
4. **Multi-Language Support (i18n)**: How should domains, questions, and answers localize?
5. **Structured Input (Query DSL)**: Should MCP-A add a query DSL (e.g., SQL-like filters) in addition to natural-language queries?
6. **Domain Versioning Policy**: How do domains evolve their schemas without breaking callers? (Deprecation windows, additive-only rules, etc.)

## References

- **SPEC.md**: §1 (discover), §2 (schema), §3 (query), §4 (follow_up), §5 (context), §6 (explain), §Aggregation Correctness Conformance, §Open Questions.
- **README.md**: Project index and positioning of MCP-A as an MCP profile.
- **RFC-PROCESS.md**: MAEP governance and publication paths.
- **POSITIONING.md**: Landscape positioning vs. RAG and relationship to MCP.
