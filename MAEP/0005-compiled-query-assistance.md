---
MAEP: 0005
Title: Compiled Query Assistance — API-surface schema, query-building discover, and query clarification
Author: Bob Matsuoka <robert@matsuoka.com>
Status: Implemented
Created: 2026-07-01
Updated: 2026-07-01
Spec-Version-Target: 1.1.0-beta
---

> **Status note (2026-07-01):** Fast-tracked Draft → Accepted → Implemented in a single step. The
> maintainer (Bob Matsuoka), who is also the author of this proposal, authorized immediate
> implementation rather than waiting out the standard two-week discussion window. Implemented into
> the normative `SPEC.md` (§1 discover guidance, §2 `api_surface`, §3 query clarification), the
> `discover`/`schema`/`query` JSON Schemas, and worked examples (01, 02, and the new 26); ships in
> spec version **1.1.0-beta** (a MINOR, additive bump). See [CHANGELOG.md](../CHANGELOG.md).

## Summary

Consolidates server-side query-assistance richness with stable primitive shapes. The feature set is three-fold: (1) **`discover` adds query guidance** — optional natural-language suggestions and structured templates/disambiguation hints — so clients learn how to construct questions upfront, while keeping discover's response shape permanently stable (no new field names, only content growth); (2) **`schema` consolidates** backend API surface transparency (OpenAPI/GraphQL SDL/SQL catalog) and hierarchical drill/action introspection, enabling backend visibility and deep ontological navigation; (3) **`query` adds a clarification path** for underspecified questions, modeled on `action`'s reactive clarification mechanism, so the server infers and repairs malformed queries server-side before returning results. All three changes are **additive** and **off by default** for Core conformance.

---

## Motivation

### Core Principle: Fixed Interface, Scalable Domain Richness

MCP-A's core value proposition is that its **seven primitives** (`discover`, `schema`, `query`, `action`, `follow_up`, `context`, `explain`) form a **FIXED interface**. Adding new backend APIs, domains, or backend technologies of wildly different kinds must **NEVER** require growing or complicating this primitive set. The interface is stable by design.

However, **domain-specific and backend-specific richness is allowed** — and necessary — to scale. The principle is: **`schema` is the ONLY primitive whose response shape is permitted to grow with backend complexity.** Every other primitive's shape remains stable no matter how many backends or how much ontological variety a server manages. This MAEP extends `schema` to consolidate and expose all domain/backend detail (API surface, query-building hints, ontological drill, action introspection) in one place, keeping `discover`, `query`, `action`, `follow_up`, `context`, and `explain` thin and stable.

---

### Current Gaps

MCP-A achieves **performance** and **precision** by moving compilation server-side. But today's `discover` and `schema` assume the client (or expensive LLM) can construct well-formed questions without help, and if a `query` arrives malformed or underspecified, the server returns `INVALID_REQUEST` (400) with no path to repair.

Three gaps emerge in practice:

### 1. Schema exposes ontology, not backend surface

`schema` returns a domain's **ontology** (entities, fields, types, relationships, allowed aggregations). This is precise for the client: it knows what it can ask and what shape an answer takes. But the server's **internal mapping** from ontology into backend queries (GraphQL mutations, REST endpoints, SQL aggregate functions) is opaque. A GraphQL backend may support raw SDL introspection; a SQL warehouse has a catalog. Exposing this surface directly (or as a reference) lets:

- Clients that want to build precise queries understand exactly what backend operations are available.
- Servers implement routing/compilation more intelligently by inspecting client intent against the full backend surface, not just the filtered ontology.
- Debugging and explanation (via `explain`) become more transparent: "I routed your question to GraphQL mutation X because you asked to Y."

The guides (`surfacing-apis.md`, etc.) already show this mapping exists *internally*; this MAEP makes it optionally **visible**.

### 2. Discover is thin; query-building hints move to schema

`discover` returns a catalog of **domains** with minimal metadata: id, name, one-line description. This keeps `discover`'s response shape **permanent** — adding new domains adds one more entry; the shape never changes no matter how many backends exist behind those domains.

Query-building guidance (templates, disambiguation hints, full API surface details) is **domain-specific and backend-specific** — it belongs in `schema`, colocated with the ontology and `api_surface` it's derived from. When a client needs construction assistance, it calls `schema(domain=X)` once (not per query), which returns all the richness needed to build well-formed questions for that domain: the ontology, templates, hints, and backend surface.

**Design decision callout**: An earlier version of this proposal placed `query_templates` and `disambiguation_hints` on `discover`, leveraging the principle that "hint the client early." However, this would require `discover` to grow each time a domain's query patterns changed or a new backend variant was added to a domain. This conflicts with the core principle (primitives are fixed, only `schema` scales). The corrected approach concentrates all domain richness in `schema`, so `discover`'s shape is permanently stable.

### 3. Query has no clarification path for underspecified questions

`query` today returns `INVALID_REQUEST` if a question is ambiguous (e.g., "Renew Acme" when three Acme accounts exist) or has missing required parameters (e.g., asking for revenue without specifying a time period). The expensive client model has to understand the error and retry with more specificity. 

MAEP-0003 adds reactive `clarification` to `action`: if an action needs fields, it returns them; the client supplies them in a continuation. This pattern is **missing from `query`**, even though query clarification is often cheaper to resolve (fewer decisions, deterministic entity lookup). A server using a cheap inference model can:

- Infer which fields disambiguate a query (e.g., "you said Acme, here are the 3 Acme accounts; which one?").
- Suggest default values for missing parameters (e.g., "revenue defaults to last 30 days").
- Return a clarification round instead of failing, so the client supplies what's needed.

This is consistent with the **Efficiency** pillar: cheap server-side inference asks for clarification; expensive client model consumes a finished result.

### Why this structure maintains the Fixed Interface principle?

Together, these three pieces form one end-to-end capability: **the server actively assists in constructing and repairing queries, with early guidance and full API-surface awareness, while keeping all primitive shapes permanently stable**. A client that:

1. Calls `discover` learns what domains this server manages and optionally receives query-building guidance (natural-language and templates) — `discover`'s shape is fixed, only content grows.
2. Calls `schema(domain=X)` learns the ontology and optionally receives API surface transparency and hierarchical drill/action introspection — `schema` handles variable-form backend detail.
3. Calls `query` with an underspecified question can receive `clarification_required` instead of failing.

This is the **Compile Server-Side** principle made proactive, AND the **Fixed Interface** principle maintained: **primitive shapes are fixed** (the field names on each response are determined once and never change); **only content scales** (the number of domains, templates, hints, and ontological detail). The seven primitives' shapes remain stable forever, while their content richness scales freely.

---

## Specification

*Normative. Implementations that claim this feature MUST conform to this section. These changes extend `discover`, `schema`, and `query` without breaking existing requests.*

### 5.1 Discover Domain Catalog with Query Guidance

`discover.response.json` returns a list of available domains with optional query-building guidance. Per this MAEP, **discover's response shape remains fixed and stable** — it never grows with domain count, backend technology, or API complexity.

#### Base: Domain Catalog (Unchanged)

```json
{
  "domains": [
    {
      "id": "storefront-graphql",
      "name": "Storefront",
      "description": "Ecommerce orders, customers, and products.",
      "natural_language_guidance": "Ask questions like 'How many customers placed orders last month?' or 'What is the average order value for high-value customers?'",
      "query_templates": [
        {
          "template": "revenue by {time_period} for {customer_type}",
          "variables": [
            { "name": "time_period", "values": ["day", "week", "month", "quarter", "year"] },
            { "name": "customer_type", "values": ["all", "new", "active", "churned"] }
          ]
        },
        {
          "template": "list {entity_type} matching {filter_name}",
          "variables": [
            { "name": "entity_type", "values": ["customers", "orders", "products"] },
            { "name": "filter_name", "values": ["active", "high_value", "at_risk"] }
          ]
        }
      ],
      "disambiguation_hints": [
        {
          "field": "customer_id",
          "description": "Required when asking about a specific customer. Provide the numeric ID; ambiguous names will be disambiguated via clarification round.",
          "example": "12345"
        },
        {
          "field": "time_period",
          "description": "Defaults to 'last 30 days' if not specified.",
          "example": "Q3 2026"
        }
      ]
    },
    {
      "id": "analytics-sql",
      "name": "Analytics",
      "description": "Historical sales and customer analytics."
    }
  ]
}
```

**Base fields** (as per SPEC):

- **`id`** (required): Domain identifier.
- **`name`** (required): Human-readable name.
- **`description`** (required, or SHOULD be present): One-line description of the domain.

**Query guidance fields** (optional):

- **`natural_language_guidance`** (string, optional): Prose suggestions and example questions for querying this domain. Helps clients understand what kinds of questions this domain can answer.

- **`query_templates[]`** (array, optional): Structured query patterns the domain prefers. Each template:
  - `template` (string): Human-readable pattern with `{variable}` placeholders.
  - `variables[]`: Enumerated choices for each placeholder.
  - Allows clients to construct queries by template instantiation instead of free-form text.

- **`disambiguation_hints[]`** (array, optional): Common fields that often require clarification:
  - `field` (string): Field name or concept (e.g., "customer_id", "time_period").
  - `description` (string): Guidance on what the field is and what happens if omitted.
  - `example` (string): An example value.
  - Helps clients understand what the server may ask for in a clarification round.

#### Why Guidance Scales Efficiently (Fixed-Shape Principle)

Discover's **response shape** (the number and names of fields per domain) is stable and never grows. When implementations add new domains, backends, or query patterns, **only the `domains[]` array grows** — the per-domain shape remains unchanged. This is the **fixed-shape, bounded-content distinction**:

- **Shape** (field names, structure): Determined once, never changes. `discover` always has `id`, `name`, `description`, and optionally `natural_language_guidance`, `query_templates`, `disambiguation_hints`. A Core server omits guidance fields; a Full server includes them.
- **Content** (what values go into those fields): Grows freely. Adding a new domain, new templates, or new hints is a content change, not a shape change.

This is fundamentally different from `schema`'s `api_surface`, which is a **large, variable, technology-specific** blob (raw OpenAPI, GraphQL SDL, or SQL catalog) that changes form depending on the backend. Discover's guidance is a **small, structured, fixed-schema** object: its shape is determined upfront and never changes, only the content (number of templates, number of hints, etc.) evolves. A client parsing `discover` always knows the fields to expect; it never has to discover new fields as the server evolves.

#### Metadata-Derived Guidance

Implementers **SHOULD** auto-derive query guidance from the underlying backend's own metadata rather than hand-authoring it. Examples:

- **GraphQL backends**: Extract operation summaries/descriptions from GraphQL SDL and turn them into templates and natural-language guidance.
- **REST backends**: Use OpenAPI operation descriptions and parameter schemas to generate templates.
- **SQL backends**: Use table/column comments and schema to generate templates and field hints.

This approach reduces server-implementer authoring burden and ensures guidance stays in sync with the actual backend as APIs are added or evolve, keeping the "buildout of underlying APIs without increasing complexity" principle: new backends and new domains add content to discover, not new fields.

**Conformance**:

- Discover's response **shape** is **stable and does not grow** across all versions and deployments. A Core server omits all guidance fields; a Full server **MAY** include them.
- Discover's response **content** (the array length, the content of templates and hints) is free to grow as new domains, templates, or patterns are added.
- If a server wishes to signal protocol/session/capability negotiation beyond domain listing, that belongs in a separate optional field at the top level of `discover.response` (e.g., `capabilities` or `protocol_version`), not in the domain entry.
- Clients **SHOULD** gracefully handle domains with or without guidance fields (guidance is optional).

### 5.2 Schema Consolidation (Ontology, API Surface, Hierarchical Drill)

**Consolidates backend-specific transparency and deep ontological navigation into one primitive response.** `schema.response.json` extends with two layers of detail:

#### Layer 1: Ontology (existing, unchanged)

The domain's normalized entity/field/relationship model:

```json
{
  "domain_id": "storefront-graphql",
  "schema_version": "1.0",
  "entities": [ ... ],
  "fields": [ ... ],
  "relationships": [ ... ],
  "allowed_aggregations": [ ... ]
}
```

#### Layer 2: API Surface (optional, Full-tier)

Exposes the underlying backend surface (OpenAPI, GraphQL SDL, SQL catalog):

```json
{
  "domain_id": "storefront-graphql",
  "schema_version": "1.0",
  "entities": [ ... ],
  "api_surface": {
    "format": "graphql-sdl",
    "spec": "type Order { id: ID! customer: Customer! total: Float! ... } type Query { orders(filter: OrderFilter): [Order!]! } mutation CreateOrder { ... }"
  }
}
```

**Fields**:

- **`api_surface.format`** (required when `api_surface` is present): One of:
  - `openapi-3.1` — OpenAPI 3.1.x specification, typically JSON or YAML
  - `graphql-sdl` — GraphQL Schema Definition Language (string)
  - `sql-catalog` — SQL table/view schema (database-specific syntax or standardized format)
  - `other` — Implementation-defined format (server MUST document it)

- **`api_surface.spec`** (required when present): Either:
  - Inline (string or object): The full or summary API specification.
  - Reference (string starting with `http://` or `https://`): A URI the client can fetch.

**Note on N-APIs-to-1-Domain**: A single domain (e.g., "storefront-graphql") may be backed by one or more underlying APIs (one GraphQL endpoint, or a composition of REST + cached SQL). The `api_surface` field describes the backend surface *as exposed by this server* for this domain. The ontology is the normalized client-facing view; the api_surface is the backend transparency view. When a domain spans multiple backend APIs, the server combines them into a single `api_surface` description (or lists multiple `api_surface` entries if the backends are truly separate), normalizing the N-to-1 mapping transparently.

#### Layer 3: Hierarchical Drill & Action Introspection (MAEP-0004)

See [MAEP-0004](./0004-hierarchical-schema.md) for extensions to `schema` supporting hierarchical drilling (`path`, `depth`) and action-schema introspection (`target: action`). This MAEP's extensions (§5.2 Layers 2–3 above) are sibling enhancements; both coexist in a single `schema.response`.

---

**Conformance**:

- The `api_surface` block is **OPTIONAL** and **additive** — existing schema responses remain valid.
- If present, it **MUST** be **accurate** and actionable — clients will rely on it.
- A server **SHOULD** include `api_surface` when the underlying backend has a formally-defined API surface (GraphQL endpoint with SDL, REST service with OpenAPI, SQL warehouse with schema).
- A server **MUST NOT** include `api_surface` unless it accurately reflects the **actual backend surface** — it is a debug/transparency aid and MUST be trustworthy.
- When `api_surface` is present, the `entities`/`fields`/`aggregations` in the ontology **MUST** be mappable to constructs in the exposed surface (though the ontology MAY be a *filtered* or *abstracted* view).

**Cache semantics**: A response that includes `api_surface` remains cacheable per `(domain_id, target, path, depth)`, same as the pre-MAEP schema response.

### 5.3 Query Clarification Path

Extends `query.response.json` to include an optional `clarification_required` status and a `clarification` object matching the pattern established by `action` (MAEP-0003):

```json
{
  "answer_id": "ans-7f2e91",
  "status": "clarification_required",
  "summary": "Your question refers to 'Acme', but there are 3 accounts with that name. Please disambiguate.",
  "clarification": {
    "needed": [
      {
        "name": "customer_id",
        "description": "Which Acme account? (1) Acme Corp [ID: 12045], (2) Acme Industries [ID: 12891], (3) Acme LLC [ID: 15302]",
        "type": "string",
        "enum": ["12045", "12891", "15302"],
        "required": true
      }
    ],
    "prompt": "Please select the Acme account you meant."
  },
  "citations": [],
  "timestamp": "2026-07-01T15:23:00Z"
}
```

**Response shape**:

- **`status`**: When the server needs more information, **MUST** be `clarification_required` (instead of returning `INVALID_REQUEST` 400).
- **`clarification`**: Present **if and only if** `status` is `clarification_required`. Structure:
  - `needed[]` (`ClarificationField[]`): Uses the same `$def` from `common.defs.json` as `action` (SPEC §action clarification). Each field specifies:
    - `name` (required): Key the client uses in the continuation.
    - `description` (required): Human-readable explanation.
    - `type` (optional): Expected type (`string`, `integer`, `boolean`, etc.).
    - `enum` (optional): Allowed values, when constrained.
    - `example` (optional): Sample value.
    - `required` (optional, default true): Whether the server cannot proceed without it.
  - `prompt` (optional): High-level prompt to show the user.

**Continuation request** — the client calls `query` again with the same `query_id` plus additional context:

```json
{
  "question": "What is the revenue for Acme?",
  "user_id": "u-4471",
  "domain_id": "storefront-graphql",
  "query_id": "ans-7f2e91",
  "clarification_inputs": { "customer_id": "12045" }
}
```

**Field**:

- **`query_id`** (string): The `answer_id` from the prior clarification response. Signals a continuation.
- **`clarification_inputs`** (object): A map of field names (from `clarification.needed[].name`) to supplied values.

**Server behavior**:

- A server **MUST** attempt best-effort **server-side inference** before returning `clarification_required`. Examples:
  - Detect ambiguous entity references and return specific disambiguation options.
  - Infer missing aggregation dimensions from context or defaults.
  - Suggest or fill in optional time periods.
  - Only when the server **cannot** disambiguate or infer SHOULD it return `clarification_required`.
- When a client provides `clarification_inputs`, the server reuses the prior answer's routing context (the prior `answer_id`) and incorporates the clarifications, then attempts to compile a full answer.
- If still clarification is needed after a round, the server **MAY** return another `clarification_required` with a new set of `needed` fields. This is allowed but servers **SHOULD** minimize round-trips by asking for all needed fields at once.
- The server **MUST** still support the prior error behavior: if a question is **unparseable** (no identifiable domain, unrecognizable question syntax, etc.), the server **MAY** return `INVALID_REQUEST` instead of `clarification_required`. The distinction:
  - `clarification_required`: "I understood the intent but lack specificity; here's what I need."
  - `INVALID_REQUEST`: "I cannot parse this at all."

**Conformance**:

- This feature is **OPTIONAL** (Core servers do not need to implement clarification; they may continue returning `INVALID_REQUEST`).
- A server that implements clarification **MUST**:
  - Attempt inference before returning `clarification_required`.
  - Use the `ClarificationField` $def exactly (reuse from `action`, no query-specific variant).
  - Support the `query_id` + `clarification_inputs` continuation format.
  - Preserve the prior answer's routing decision across clarification rounds (for efficiency; this mirrors `follow_up`'s **reuse prior routing** principle).
  - Transparently report what it inferred vs. what it is asking for (via `summary` and `clarification.prompt`).
- Clients **MUST NOT** assume a server supports clarification; they SHOULD gracefully degrade if `status` is not `clarification_required` (e.g., fall back to rephrasing the question).

### 5.4 Interactions with existing primitives

- **discover** — Adds optional query guidance fields (`natural_language_guidance`, `query_templates`, `disambiguation_hints`). The response **shape** is stable and fixed; only the **content** of these optional fields grows. A Core server omits guidance; a Full server may include it.
- **schema** — Consolidates backend transparency: `api_surface` (raw API surface for debug/routing) and hierarchical/action introspection (MAEP-0004). The response handles variable-form backend detail (per the core principle). Query guidance is NOT in schema; it lives in discover.
- **action** — Unchanged. `action` has its own `clarification` mechanism (MAEP-0003); `query` clarification is independent (read-side only; no state changes).
- **follow_up** — Unchanged. `follow_up` refines a prior answer; `query` clarification is a distinct path for the initial question.
- **explain** — Unchanged. `answer_id` remains usable with `explain` to inspect how a question (including clarified versions) was routed.
- **context** — Unchanged. Session management and user preferences remain independent.

### 5.5 Error codes

No new error codes. Servers reuse existing codes:

- `INVALID_REQUEST` — when the question is truly unparseable (fallback, used less often now that clarification is available).
- `UNAUTHENTICATED`, `FORBIDDEN`, `TIMEOUT`, `DOMAIN_NOT_FOUND` — as before.

Servers implementing clarification **MUST** be thoughtful: they should return `clarification_required` (status, not error) when they can articulate what is needed, and `INVALID_REQUEST` (error) only when they truly cannot.

---

## Rationale and Alternatives

### Why expose the backend API surface?

A domain's ontology is a *filtered, normalized* view. The actual backend (GraphQL, REST, SQL) may support operations or fields the ontology does not expose. Exposing the surface:

- Allows developers to audit the mapping and debug routing logic.
- Lets clients understand the full capabilities of a domain (not just the MCP-A filtered view).
- Enables future routing/compilation to leverage backend-specific operations not yet surfaced in the ontology.
- Remains **optional** and **transparent** — clients that don't care about the surface can ignore it.

**Alternative considered**: Mandate that the ontology is a complete, faithful projection of the backend. *Rejected* because (1) most backends expose fields the server intentionally filters for RBAC or simplicity, and (2) hiding the surface makes debugging and evolution harder. The surface is an implementation detail that implementers *should* be able to share when it's safe to do so.

### Why place query templates and hints in discover, not schema?

Query templates and disambiguation hints are **domain-specific and backend-specific** — they change when a domain's ontology evolves, or when new backend variants are added to a domain. Placing them in `discover` (not schema) ensures:

- **Discover remains thin and conceptually stable**: Discover's **response shape** (the field names: `id`, `name`, `description`, `natural_language_guidance`, `query_templates`, `disambiguation_hints`) is permanently fixed. Adding new domains, evolving domain patterns, or adding backend variants to a domain does NOT change the shape — only the `domains[]` array content and the content of guidance fields change.
- **Fixed-shape vs. variable-content distinction**: Unlike `schema`'s `api_surface` (which is a large, opaque, technology-specific blob), discover's guidance fields are small, structured, fixed-schema objects. Their shape is determined upfront and never changes; only their content (the number of templates, the number of hints) scales with domain complexity. This allows discover to hint the client early without violating the core principle of fixed interface and stable shape.
- **Core principle maintained**: The seven primitives' **shapes** stay fixed; only the **content** of domain-specific fields scales. `Schema`'s `api_surface` is a variable-form blob; discover's guidance is a fixed-form bounded object. Both live in their respective primitives without growing the primitive count.
- **Efficient metadata derivation**: Guidance can be auto-derived from the underlying backend's own metadata (GraphQL descriptions, OpenAPI summaries, SQL comments) without manual curation, reducing server-implementer burden and keeping guidance in sync as backends evolve.

**Alternative considered**: Place templates/hints in `schema`, claiming that all domain richness belongs there. *Rejected* because (1) clients benefit from discovering basic guidance early (in `discover`), and (2) the scope of guidance is bounded and structured, not a variable-form blob like `api_surface`, so it doesn't violate the fixed-shape principle when placed on `discover`.

### Why query-side clarification, not just action-side?

Read-side (`query`) clarification is often **easier and cheaper** to resolve than write-side (`action`). Disambiguating "Acme" to an account ID is a lookup; asking for confirmation on a destructive action is a policy decision. Offering clarification on both sides:

- Keeps the paths **independent** and appropriate to each primitive's purpose.
- Avoids forcing read questions into the write-side (`action` is for state changes, not queries).
- Reuses the proven `clarification` pattern from `action` (MAEP-0003) for consistency.

**Alternative considered**: Only clarify via `action`, route all ambiguous reads to action-like "select and then read" flows. *Rejected* because (1) it conflates read and write semantics, and (2) most read clarifications don't require the heavyweight action protocol.

### Why reuse ClarificationField from action, not a query-specific variant?

The `ClarificationField` $def is general: `{ name, description, type, required, example, enum }`. It works for both action inputs and query disambiguations. Reusing it:

- Reduces schema surface area.
- Lets clients reuse parsing/rendering logic.
- Maintains consistency across the spec.

**Alternative considered**: Define a distinct `QueryClarificationField` with query-specific semantics (e.g., suggestion for default values). *Rejected* because the base $def is sufficient; defaults can live in `description` or `example`.

---

## Backwards Compatibility

This MAEP is **additive** — a **MINOR** version bump.

- **Discover**: No changes to structure; existing `discover` responses remain valid indefinitely. Servers do not add new fields to `discover`.
- **Schema**: Every new field (`api_surface`, `query_templates`, `disambiguation_hints`) is **OPTIONAL**. An existing client that ignores unknown response fields (per SPEC §Versioning & Extension) sees no change.
- **Query**: Every new field in requests (`query_id`, `clarification_inputs`) and responses (`status: clarification_required`, `clarification`) is **OPTIONAL**.
- An existing server that does not implement the new fields simply omits them; clients MUST NOT assume they are present.
- A `query` request with only `question`, `user_id`, and `domain_id` (no `query_id` or `clarification_inputs`) is unchanged; no existing client breaks.
- A `query` response with `status: clarification_required` is **new** behavior that only non-legacy servers will return; existing clients that only handle `status: completed` or `error` continue to work, they just won't see clarifications (will see `INVALID_REQUEST` instead on servers that don't implement clarification).
- **Conformance tier**: These features are **Full-tier** (not Core). A Core server is read-only and MUST NOT implement `api_surface` or query clarification (Core servers can return `INVALID_REQUEST` as they do today). A Full server **MAY** implement any subset of these capabilities.

No existing conformant implementation becomes non-conformant.

---

## Reference Implementation

Planned alongside MAEP-0001/0003/0004 in the `mcp-a-spec` repo. Gotchas for implementers:

- **API surface accuracy**: The `api_surface` block **MUST** match the actual backend schema; if it drifts, clients will be confused. Recommend automated sync from backend introspection (e.g., GraphQL's `__schema` introspection, OpenAPI codegen, SQL schema snapshot).
- **Inference quality**: Query clarification relies on heuristics to disambiguate and infer. A server SHOULD have clear rules for when to infer vs. when to ask. Example: "If I see a potential entity reference with multiple matches, ask; if I see a missing aggregation dimension with a sensible default, infer it."
- **Routing reuse**: When a client provides `clarification_inputs` on a `query_id`, the server reuses the prior routing decision (the `answer_id`'s domain/source decisions). This mirrors `follow_up`'s efficiency principle but requires the server to maintain state briefly (`answer_id` → prior routing context) — same burden as `follow_up` already imposes.
- **State cleanup**: `answer_id` + `query_id` + clarification context (the user's answers to prior clarification) MUST be garbage-collected after clarification rounds complete or expire. Recommend a TTL (e.g., 5–10 minutes) matching `answer_id` expiry.

---

## Open Questions

- **`api_surface` schema format**: Should we standardize on OpenAPI 3.1 as the canonical format, and recommend servers translate other formats (GraphQL SDL, SQL catalog) to OpenAPI for consistency? Or allow multiple formats and let clients choose?
- **Query clarification depth**: Should the spec bound the number of clarification rounds (e.g., max 2–3 rounds before the server returns `INVALID_REQUEST`)? Or leave it to implementation?
- **Template variable constraints**: Should `query_templates` support richer variable schemas (e.g., `{ "type": "date", "range": ["2026-01-01", "2026-07-01"] }`) instead of just `enum`? How much structure is useful without over-specifying?
- **Conformance tier placement**: Are these features solidly **Full-tier**, or should servers be able to claim a "Full" conformance without implementing query clarification (making it a separate capability gate)? Current assumption: all three (api_surface, query_templates, clarification) are Full-tier enhancements; a Full server MAY implement a subset, but the feature set as a whole is Full.
- **ClarificationField reuse**: Should there be a query-specific variant of `ClarificationField` (e.g., adding a `suggested_value` or `inferred_from` field to explain what the server inferred vs. what it is asking for)? Or is the base $def sufficient with explanation in `description`?

---

## References

- [GitHub issue #7](https://github.com/bobmatnyc/mcp-a-protocol/issues/7) — Original discussion and proposal thread
- [SPEC.md](../SPEC.md) — §1 discover, §2 schema, §3 query; §Terminology (Clarification, Ontology); §Design Principles; §Conformance Levels
- [MAEP-0003](./0003-action-primitive.md) — The `action` primitive and its `clarification` mechanism; this MAEP applies the same pattern to `query`
- [MAEP-0004](./0004-hierarchical-schema.md) — Hierarchical and operation-aware `schema`; this MAEP's `api_surface` field is a sibling extension to the MAEP-0004 drilling/introspection enhancements
- [CONFORMANCE.md](../CONFORMANCE.md) — Conformance levels (Core vs. Full); these features are Full-tier
- [schemas/common.defs.json](../schemas/common.defs.json) — The `ClarificationField` $def reused here
- [guides/surfacing-apis.md](../guides/surfacing-apis.md) — Background on how backends are mapped to the MCP-A ontology; this MAEP makes that mapping partially visible
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — MUST/SHOULD/MAY semantics
