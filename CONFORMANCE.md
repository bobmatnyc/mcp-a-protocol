---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-18
---

# MCP-A Conformance Matrix

A checkable, self-audit conformance guide for MCP-A v1.0-beta. Every requirement traces back
to a section of [`SPEC.md`](./SPEC.md). Use the checkboxes to audit an implementation; declare
your level in the `discover` response's `server` block (see
[How to claim conformance](#how-to-claim-conformance)).

Keyword conventions (MUST / SHOULD / MAY) follow RFC 2119, as in the spec.

## Conformance levels

Pulled from [SPEC §Conformance Levels](./SPEC.md#conformance-levels). A server MUST declare
one level, and `server.conformance_level` MUST accurately reflect what it implements (SPEC §1).

| Level | Primitives required | Features required |
|-------|---------------------|-------------------|
| **Core** | `query` + `context` | Single-turn personalized **prose** answers. `supported_primitives` MUST list at minimum `["query", "context"]`. Prose-only is acceptable. |
| **Full** | all six: `discover`, `schema`, `query`, `follow_up`, `context`, `explain` | Everything in Core **plus**: domain ontology/schema introspection (`schema`), **structured-response mode** on `query` (tagged `response_schema` → typed `structured` output), the required `server` capability block on `discover`, and Aggregation Correctness. `supported_primitives` MUST list all six. Recommended for production. |
| **Extended** | Full | Full + vendor-specific extensions (e.g., custom drill tools, feedback models). MUST satisfy **all** Full requirements before declaring Extended. |

Notes (SPEC §Conformance Levels):

- A server MUST NOT declare `Full` unless all six primitives are implemented (SPEC §1).
- A server MUST NOT declare `Extended` unless it satisfies all Full requirements.
- `schema` introspection and structured-response mode are **Full**, not Core — a Core server
  MAY return prose only.
- Clients SHOULD call `discover` to read `server.supported_primitives` before calling any
  primitive, and SHOULD call `schema` before relying on structured-response mode.

### Feature-to-level cross-check

| Feature | Core | Full | Extended |
|---------|:----:|:----:|:--------:|
| `query` (prose) | ✅ | ✅ | ✅ |
| `context` (identity, prefs, access scope) | ✅ | ✅ | ✅ |
| `discover` (RBAC-filtered catalog) | — | ✅ | ✅ |
| `server` capability block on `discover` | — | ✅ | ✅ |
| `schema` (ontology introspection) | — | ✅ | ✅ |
| `query` structured-response mode (`response_schema`) | — | ✅ | ✅ |
| Aggregation Correctness (deterministic rollups) | — | ✅ | ✅ |
| `follow_up` (refine / drill / poll) | — | ✅ | ✅ |
| `explain` (routing, alternatives, latency/confidence) | — | ✅ | ✅ |
| Vendor extensions | — | — | ✅ |

---

## Per-primitive checklist (normative MUST / SHOULD)

Each item cites the SPEC section it derives from. `[Core]` marks requirements that already
apply at Core; unmarked items apply at the level where the primitive is required (Full for
`discover`, `schema`, `follow_up`, `explain`).

### 1. `discover` — SPEC §1

- [ ] **MUST** filter domains by the user's access scope; a domain the user cannot access **MUST NOT** appear. (SPEC §1, §RBAC)
- [ ] **MUST** include the `server` block with `mcp_a_version`, `conformance_level`, and `supported_primitives` in **every** response. (SPEC §1)
- [ ] **MUST** make `conformance_level` accurately reflect what the server implements; **MUST NOT** declare `Full` unless all six primitives are implemented. (SPEC §1, §Conformance Levels)
- [ ] **MUST** support `semantic_filter` as an optional substring/keyword match over domain names and descriptions. (SPEC §1)
- [ ] **MUST** return `freshness_seconds` for each domain. (SPEC §1)
- [ ] **MUST** be cacheable by clients (suggested TTL 5–60 min). (SPEC §1)
- [ ] **SHOULD** support pagination or `limit` for large catalogs. (SPEC §1)
- [ ] **MAY** mark domains `deprecated` / `read-only` via the optional `status` field. (SPEC §1)
- [ ] Error modes: `UNAUTHENTICATED`, `FORBIDDEN`, `INVALID_REQUEST`. (SPEC §1)

### 2. `schema` — SPEC §2

- [ ] **MUST** return the ontology for a domain the user can access; **MUST** return `FORBIDDEN` for domains outside the user's access scope. (SPEC §2, §RBAC)
- [ ] **MUST** list, per field, only the aggregations the domain computes deterministically server-side (see [Aggregation Correctness](#aggregation-correctness--spec-aggregation-correctness-conformance)). (SPEC §2)
- [ ] **SHOULD** return `schema_version` so callers can detect ontology changes. (SPEC §2)
- [ ] **SHOULD** be cacheable (longer TTL than `discover`). (SPEC §2)
- [ ] **MAY** omit relationships or aggregations when the caller sets the corresponding `include_*` flag false. (SPEC §2)
- [ ] Error modes: `UNAUTHENTICATED`, `FORBIDDEN`, `DOMAIN_NOT_FOUND`. (SPEC §2)

### 3. `query` — SPEC §3

**Core (prose) requirements:**

- [ ] **MUST** classify the question against available domains and route to relevant source systems in parallel. (SPEC §3)
- [ ] **MUST** return citations with at least `source_system`, preferably a snippet or entity reference. (SPEC §3)
- [ ] **MUST** respect the user's access scope: silently filter records the user cannot see (no error). (SPEC §3, §RBAC)
- [ ] **MUST** return an `answer_id` so the answer can be referenced by `follow_up` and `explain`. (SPEC §3)
- [ ] **MUST** support `timeout_seconds` and return a best-effort draft if full compilation takes longer. (SPEC §3)
- [ ] **MUST NOT** cache a compiled answer across different users, even for an identical question. (SPEC §3)
- [ ] **SHOULD** include confidence when requested; **MUST NOT** return confidence > 0.95 for multi-source fan-out answers without human review. (SPEC §3)
- [ ] **MAY** return `recommended_tool` to guide drilling deeper. (SPEC §3)
- [ ] Error modes: `INVALID_REQUEST`, `UNAUTHENTICATED`, `FORBIDDEN`, `TIMEOUT`, `SCHEMA_NONCONFORMANT`, `SOURCE_UNAVAILABLE`. (SPEC §3)

**Structured-response mode (Full) — SPEC §3 Structured-Response Mode:**

- [ ] When `response_schema` is supplied with an explicit `kind` discriminator, **MUST** return `structured` conforming to that schema, **or** fail with `SCHEMA_NONCONFORMANT` — **MUST NOT** silently downgrade to prose-only without signaling. (SPEC §3)
- [ ] **MUST** apply server-side aggregations and disambiguation to produce typed values; aggregated fields **MUST** be computed, not LLM-estimated. (SPEC §3, §Aggregation Correctness)
- [ ] **MUST** set `structured_schema_ref` to the schema/ontology the payload conforms to. (SPEC §3)
- [ ] **MUST** still return `citations` for structured payloads. (SPEC §3)
- [ ] When `include_prose=true`, **MUST** return a short prose `answer` summary; when `include_prose=false`, `answer` **MAY** be omitted or null. (SPEC §3)
- [ ] An aggregation requested via the schema **MUST** be one the target domain declares allowed in its `schema` response; otherwise fail with `AGGREGATION_NOT_ALLOWED`. (SPEC §3, §Aggregation Correctness)

### 4. `follow_up` — SPEC §4

- [ ] **MUST** reuse the prior routing decision unless the refinement semantically requires re-routing. (SPEC §4)
- [ ] **MUST NOT** require re-authentication per follow-up; but **MUST** re-evaluate RBAC at follow-up time — if the user's access scope changed since the prior `query`, the answer **MUST** reflect the current scope. (SPEC §4, §RBAC)
- [ ] **MUST** support `drill_tool_id` to focus on a specific source system from the prior answer's `recommended_tool`. (SPEC §4)
- [ ] For long-running compiles, **MUST** support polling via repeated `follow_up` calls and return a `status` field (`pending` / `complete`). (SPEC §4)
- [ ] **SHOULD** keep refinements cheap — avoid re-fanning to all sources for a pure narrowing; apply post-hoc filtering when possible. (SPEC §4)
- [ ] Error modes: `INVALID_REQUEST`, `UNAUTHENTICATED`, `ANSWER_NOT_FOUND`, `TIMEOUT`. (SPEC §4)

### 5. `context` — SPEC §5

- [ ] **MUST** return the authenticated user's current identity and access scope. (SPEC §5) `[Core]`
- [ ] **MUST** return preferences so clients can adjust output formatting, language, etc. (SPEC §5) `[Core]`
- [ ] **MUST** allow clients to update preferences without affecting other users. (SPEC §5) `[Core]`
- [ ] **MUST** re-evaluate access scope on every `context` read (not cached); it is the RBAC source of truth. (SPEC §5, §RBAC) `[Core]`
- [ ] **MUST NOT** leak another user's access scope or context. (SPEC §5, §RBAC) `[Core]`
- [ ] Memory (recent domains, prior answers) is **OPTIONAL** but **RECOMMENDED** for multi-turn UX. (SPEC §5)
- [ ] Error modes: `UNAUTHENTICATED`, `INVALID_REQUEST`. (SPEC §5)

### 6. `explain` — SPEC §6

- [ ] **MUST** provide a human-readable explanation of the routing decision. (SPEC §6)
- [ ] **MUST** include alternative routings considered but not chosen, with their scores. (SPEC §6)
- [ ] **MUST** return per-source latencies and confidences so clients can judge answer quality. (SPEC §6)
- [ ] **MUST** accept and record feedback (helpful, expected sources) to improve future routing. (SPEC §6)
- [ ] **MUST NOT** share other users' feedback in the explain response. (SPEC §6, §RBAC)
- [ ] **SHOULD** anonymize feedback before using it to train routing models. (SPEC §6)
- [ ] Error modes: `INVALID_REQUEST`, `UNAUTHENTICATED`, `ANSWER_NOT_FOUND`. (SPEC §6)

---

## Aggregation Correctness — SPEC §Aggregation Correctness Conformance

These rules uphold the **Precision** pillar ("correct rollups, not LLM-estimated") and are
mandatory wherever aggregations are advertised or returned (Full and Extended). They are
auditable against any `schema` and `query` (structured) response.

- [ ] A domain **MUST NOT** advertise (in a field's `allowed_aggregations`) or return any aggregation that was estimated, derived, or produced by an LLM. (SPEC §Aggregation Correctness)
- [ ] All advertised aggregations **MUST** be computed deterministically server-side — DB queries, GraphQL resolvers, or direct computation — **not** via learned model inference. (SPEC §Aggregation Correctness)
- [ ] If a domain cannot compute an aggregation deterministically, it **MUST NOT** list it as allowed. (SPEC §Aggregation Correctness)
- [ ] A structured `query` with server-side aggregation **MUST** yield a precise (computed) `structured` result, never a model approximation. (SPEC §Aggregation Correctness)

> Audit tip: every aggregation appearing in a structured `query` response (e.g., the `sum` of
> `arr` in `examples/04-query-structured.response.json`) MUST be present in that field's
> `allowed_aggregations` in the domain's `schema` response (`examples/02-schema.response.json`).
> A `sum` requested on a field that allows only `avg`/`min`/`max` MUST fail with
> `AGGREGATION_NOT_ALLOWED` (see `examples/07-error-aggregation.*`).

---

## Capability block — SPEC §1, §Conformance Levels

The `discover` response's `server` block is the single source of truth for capability
negotiation. (Required at Full/Extended, since `discover` is a Full primitive.)

- [ ] `server` block is present on **every** `discover` response. (SPEC §1)
- [ ] `server.mcp_a_version` is set (e.g., `"1.0-beta"`). (SPEC §1)
- [ ] `server.conformance_level` is one of `Core` / `Full` / `Extended` and is accurate. (SPEC §1, §Conformance Levels)
- [ ] `server.supported_primitives` lists exactly the primitives the server exposes; absent primitives **MUST NOT** be called by clients. (SPEC §1)

---

## RBAC — SPEC §Access Scope & RBAC Model

Every primitive that returns user-scoped data MUST enforce RBAC (SPEC §RBAC Authorization per
Primitive). Applies at the level where each primitive is required.

- [ ] **discover**: filter domains by the user's roles/teams. (SPEC §RBAC)
- [ ] **schema**: return `FORBIDDEN` for any `domain_id` outside the user's access scope. (SPEC §RBAC)
- [ ] **query**: filter source systems and results by access scope; remove inaccessible records silently. (SPEC §RBAC)
- [ ] **follow_up**: inherit the prior answer's RBAC and re-evaluate at follow-up time; return updated scope or `FORBIDDEN` if access was revoked. (SPEC §RBAC)
- [ ] **context**: return only the authenticated user's own context. (SPEC §RBAC) `[Core]`
- [ ] **explain**: return routing only for the user's own answers (matched by `answer_id` + `user_id`). (SPEC §RBAC)
- [ ] General: authenticate, evaluate RBAC, filter results, and re-evaluate per-request (never cache across requests). (SPEC §General RBAC Requirements) `[Core]`

---

## How to claim conformance

1. Implement the primitives and features for your target level (table above).
2. Self-audit against the checklists; every applicable box must be checked.
3. **Declare your level in the `discover` response's `server` block** — this is how clients
   discover what you support (SPEC §Conformance Levels):

   ```json
   "server": {
     "mcp_a_version": "1.0-beta",
     "conformance_level": "Full",
     "supported_primitives": ["discover", "schema", "query", "follow_up", "context", "explain"]
   }
   ```

   - `conformance_level` MUST be accurate. Do not declare `Full` without all six primitives,
     and do not declare `Extended` without satisfying all Full requirements (SPEC §1).
   - `supported_primitives` MUST list exactly what you expose. Clients MUST NOT call a
     primitive that is absent from this list (SPEC §1).

A **Core** server exposing only prose answers declares
`"conformance_level": "Core"` with `"supported_primitives": ["query", "context"]` (and any
others it actually implements). A client reading that block knows not to attempt
structured-response mode.

See [`examples/`](./examples/) for a `Full`-level server's responses, and
[`QUICKSTART.md`](./QUICKSTART.md) to build one.
