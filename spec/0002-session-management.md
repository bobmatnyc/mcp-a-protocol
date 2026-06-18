---
MAEP: 0002
Title: Session Management — Core Hook + Full-Tier Capability
Author: Robert Matsuoka <bob@matsuoka.com>
Status: Draft
Date: 2026-06-18
Spec-Version: 1.0-beta
---

## Summary

MAEP-0002 proposes reserving an OPTIONAL `session_id` field in the MCP-A core request/response shapes (`query`, `follow_up`, `context`) while placing all session lifecycle machinery — start, refresh, end, TTL/eviction, affinity — in a Full-tier capability advertised via the `server` block in `discover`. Core servers MAY ignore `session_id`; the field name and semantics are standardized now so they need not be retrofitted as a breaking change later.

This MAEP is a **proposal for review**. It does NOT modify SPEC.md or any JSON Schema files. Schema changes and SPEC.md amendments are applied only upon acceptance.

---

## Motivation

### The Missing Middle Tier of State

MCP-A currently provides two tiers of conversational state:

- **Per-answer**: `answer_id` + `follow_up` let a caller drill or refine a single compiled answer without re-classification. Short-lived, tightly scoped.
- **Per-user**: `context.memory` persists identity, preferences, and recent answers across arbitrary time. Durable, broadly scoped.

What is absent is a **per-session** tier: continuity across *different* questions within one coherent interaction, without bleeding into the user's long-term memory store.

A session is the natural middle: longer than a single answer, shorter than a user's lifetime. It is the unit of a "conversation" — a bounded context in which the server has already done classification, entity disambiguation, and routing work that remains valid for a window of time and that need not be repeated on every subsequent query.

### What Sessions Enable

When a server can associate a stream of queries with a session, it can reuse:

1. **Routing and classification decisions** — if the first query in a session established that "Acme" means the Acme Corp account in Salesforce CRM, subsequent queries in the session inherit that resolution. The server need not re-classify from scratch.

2. **Entity disambiguation** — "that deal" after a session that already touched a specific Opportunity does not require re-resolution. The session carries the referent.

3. **Conversational frame** — topic, domain focus, and output preferences established early in a session can persist without requiring the caller to re-specify them on every request.

4. **Recent `answer_id` ring buffer** — the server knows which answers were compiled in this session and can surface them to `follow_up` without the caller tracking them.

Together these improve **Performance** (cheaper routing per turn), **Efficiency** (less re-classification), and **Precision** (entity disambiguation is stable within a session).

### Why the Hook Belongs in Core

Retrofitting a new field into core request/response shapes after 1.0 stable is a breaking change — clients that hard-validate request shapes would reject previously-valid requests augmented with the field; servers that validate responses would fail on previously-conformant answers.

`answer_id` was placed in core for the same reason: the field name and its semantics must be agreed on early, even if many implementations ignore the value. `session_id` deserves the same treatment. A Core server that ignores `session_id` is still conformant; a Full server that honors it gains the benefits above.

### Why the Machinery Belongs in Full

Session lifecycle introduces complexity — start/refresh/end operations, TTL policy, eviction, affinity/sticky-routing across nodes — that is not appropriate for the Core conformance tier, which is designed to be implementable with minimal state. The same logic gates `schema` introspection and structured-response mode to Full: Core stays thin and stateless-friendly. Session machinery is the session counterpart to those features.

### Implementation Precedent

Implementations have surfaced a `session_id` in practice. The spec is currently behind the implementation. Formalizing the field in core (optional, ignorable) and the lifecycle in Full removes the ambiguity and prevents incompatible interpretations from diverging further.

---

## The State-Tier Taxonomy

The three tiers of state in MCP-A, as proposed:

| Tier | Mechanism | Scope | Duration | Who Manages |
|------|-----------|-------|----------|-------------|
| **Per-answer** | `answer_id` + `follow_up` | One compiled answer and its refinements | Until `answer_id` expires (server policy) | Server; `answer_id` is core |
| **Per-session** | `session_id` (proposed) | One coherent interaction across multiple distinct questions | Server-defined TTL; typically minutes to hours | Server (Full capability); client provides token |
| **Per-user** | `context.memory` | User's preferences and history across all interactions | Long-lived; explicit `clear` to remove | Server; `context` is core |

The three tiers are orthogonal. A per-session state layer does not replace `answer_id` (which is finer-grained: one answer and its follow-ups) nor `context.memory` (which is coarser-grained: the user's durable state). It fills the gap between them.

---

## Proposed Design

### Part 1: Core Hook — `session_id` Field Reservation

The following OPTIONAL `session_id` field is reserved in the core request and response shapes for `query`, `follow_up`, and `context`. Core servers MAY ignore the field; its presence MUST NOT cause a `INVALID_REQUEST` error on a conformant Core server.

**`query` request (addition):**
```json
{
  "question": "string",
  "user_id": "string",
  "session_id": "string? (OPTIONAL opaque session token; Core servers MAY ignore)"
}
```

**`query` response (addition):**
```json
{
  "answer_id": "string",
  "session_id": "string? (OPTIONAL; echoed or issued by Full servers; absent on Core servers)"
}
```

**`follow_up` request (addition):**
```json
{
  "answer_id": "string",
  "user_id": "string",
  "session_id": "string? (OPTIONAL)"
}
```

**`context` request (addition):**
```json
{
  "user_id": "string",
  "session_id": "string? (OPTIONAL; read or write context associated with this session)"
}
```

The `session_id` is an opaque string. Its structure, generation, and validation are implementation-defined. Callers MUST treat it as an opaque token and MUST NOT construct or parse it.

### Part 2: Full-Tier Capability — Session Lifecycle

A server that implements session lifecycle machinery MUST advertise it in the `server` block of the `discover` response:

```json
{
  "server": {
    "mcp_a_version": "1.0-beta",
    "conformance_level": "Full",
    "supported_primitives": ["discover", "schema", "query", "follow_up", "context", "explain"],
    "capabilities": {
      "sessions": true
    }
  }
}
```

The `capabilities.sessions` flag is OPTIONAL on Core servers (absent or `false`). A Full server that implements session lifecycle MUST set `capabilities.sessions: true`. A Core server MUST NOT set `capabilities.sessions: true`.

#### Session Operations (Full only)

When `capabilities.sessions` is `true`, the server MUST support the following session lifecycle operations. These MAY be implemented as sub-actions on the existing `context` primitive or as dedicated operations; the exact wire shape is left to a follow-on MAEP (see Open Questions). The semantic contract is:

- **`session.start`**: Create a new session for a `user_id`. Returns a `session_id`. MAY accept initial context (domain hints, entity anchors, output preferences). Server initializes the session cache with a TTL.

- **`session.refresh`**: Extend the TTL of an existing session. Clients SHOULD call this proactively before TTL expiry to avoid session eviction mid-conversation.

- **`session.end`**: Explicitly terminate a session and evict all associated cached state. Clients SHOULD call this at natural conversation boundaries to release server resources.

The server MAY evict sessions on TTL expiry without an explicit `session.end` call. After eviction, any `session_id` reference MUST be treated as if the session was never started — the server MUST NOT return stale cached state for an expired session.

#### What a Session MAY Cache

The following state categories are explicitly PERMITTED to be cached within a session:

| State | Cacheable? | Rationale |
|-------|-----------|-----------|
| Routing / intent classification decisions | YES | Cheap to re-derive if needed; improves per-turn performance |
| Entity disambiguation (e.g., "Acme" → account ID `001X`) | YES | Non-authoritative pointer; record details re-fetched fresh |
| Conversational frame (topic, domain focus, output preferences) | YES | User-set; stable within a session |
| Recent `answer_id` ring buffer | YES | Enables implicit `follow_up` context without caller tracking |
| User's access scope / RBAC evaluation | **NO** | See §Security and RBAC Constraints |
| Resolved record data (field values, aggregations) | **NO** | Data freshness MUST be honored per-request |
| Another user's context | **NO** | Confidentiality; sessions are user-scoped |

The distinction is between **routing pointers** (cacheable) and **authoritative data** (must remain fresh). A session tells the server *where* to look and *how* to interpret the question; it does not tell the server *what the answer is*.

---

## Conformance Impact

### What Changes at Core Conformance

- Core request/response shapes for `query`, `follow_up`, and `context` gain an OPTIONAL `session_id` field.
- Core servers MUST NOT return `INVALID_REQUEST` when `session_id` is present.
- Core servers MAY ignore `session_id` entirely.
- Core servers MUST NOT advertise `capabilities.sessions: true`.

No other Core requirements change.

### What Changes at Full Conformance

- Full servers that implement session lifecycle MUST advertise `capabilities.sessions: true` in the `server` block.
- Full servers with `capabilities.sessions: true` MUST implement `session.start`, `session.refresh`, and `session.end` (or equivalent).
- Full servers MUST honor `session_id` on incoming `query`, `follow_up`, and `context` requests by associating the call with the named session's cached state.
- Full servers MUST echo `session_id` in `query` and `follow_up` responses when a valid session is active.
- Full servers MUST enforce the session cache whitelist (§Proposed Design, Part 2 table) — in particular, MUST re-evaluate RBAC per-request regardless of session state.

Full servers that do not implement sessions (`capabilities.sessions` absent or `false`) are still conformant Full servers; sessions are an opt-in extension within the Full tier.

---

## Security and RBAC Constraints

### The Load-Bearing Rule: RBAC Is Never Sessionized

The SPEC is explicit: access scope is re-evaluated per-request (§Access Scope & RBAC Model, "Re-evaluate Per-Request"). This requirement is **non-negotiable** and applies without exception to session-capable servers. Sessions do not change the RBAC contract; they are invisible to the RBAC layer.

Concretely:

- A session MUST NOT cache a user's roles, team memberships, resource tags, or any derived RBAC decision.
- On every `query` or `follow_up` call, the server MUST re-fetch and re-evaluate the user's access scope from the authoritative identity/authorization system, regardless of whether a valid session is active.
- If a user's permissions change mid-session (e.g., a record is unshared, a team membership is revoked), the very next request in that session MUST reflect the current scope — the session MUST NOT serve stale access decisions.
- A session MUST NOT allow a user to access resources beyond their current RBAC scope, even if those resources were accessible when the session was created.

Violation of this rule is a **security defect**, not a conformance deviation. Implementations MUST treat session-cached routing state and RBAC state as strictly separate concerns, with separate storage and eviction policies.

### Explain Transparency for Session-Cached Decisions

Design Principle 4 of the SPEC states: "Compiled Answers Must Be Explainable." This principle extends to session-cached routing decisions. When a routing decision was reused from session cache rather than freshly computed, the `explain` response SHOULD indicate this:

```json
{
  "routing_decision": {
    "algorithm": "session-cache-reuse",
    "rationale": "Routing and entity disambiguation reused from session session-abc123 (established 4m ago). RBAC re-evaluated fresh at request time.",
    "session_cache_hit": true
  }
}
```

This transparency is important for auditing and for allowing callers to detect when a cached routing decision may have become stale (e.g., if the conversational context shifted substantially within a session).

### Session Isolation

- Sessions MUST be strictly user-scoped. A `session_id` created by user A MUST NOT be usable by user B, even if user B knows the token.
- Servers MUST validate that the `user_id` on each request matches the `user_id` that created the session. A mismatch MUST return `FORBIDDEN`.
- Sessions MUST NOT be shareable across users (e.g., for collaborative sessions). Multi-user sessions are explicitly out of scope for this MAEP.

---

## Open Questions

The following questions require community input before this MAEP can advance to Published/Under Review:

1. **Session TTL defaults**: What is a reasonable default session TTL? The right answer likely varies by deployment context (interactive chat vs. batch agent). Should the spec recommend a default (e.g., 30 minutes of inactivity) or leave it entirely implementation-defined?

2. **Affinity and sticky routing**: In a distributed deployment, should a `session_id` imply that subsequent requests are routed to the same server node (sticky routing / session affinity at the load balancer)? Or should session state be shared across nodes (requiring a distributed cache)? The spec should take a position or explicitly leave this as an implementation detail.

3. **Relationship to MCP's own transport-level session**: MCP itself has a concept of a connection-level session at the transport layer. How does the MCP-A `session_id` (semantic/application-layer) relate to the MCP transport session? Are they the same thing, or is `session_id` a distinct application-layer concept layered on top of MCP transport? This needs to be explicit to avoid implementers conflating the two.

4. **Multi-device sessions**: Should a `session_id` be usable across devices (e.g., a user starts a conversation on mobile and continues on desktop)? This would require the session token to be client-generated and portable, not server-issued. Or should sessions be tied to a single connection/device? The answer has implications for the `session.start` wire shape.

5. **Wire shape for session operations**: This MAEP proposes `session.start`, `session.refresh`, and `session.end` semantically but defers the exact wire encoding (sub-actions on `context` vs. dedicated primitive endpoints vs. JSON-RPC methods). A follow-on MAEP or an addendum to this one should settle this before acceptance.

6. **Session state visibility in `context` read**: Should a `context` read response include current session metadata (TTL remaining, domains touched in session, entity anchors established)? This would be useful for debugging and for client-side session management, but adds complexity to the `context` response shape.

---

## Decision Needed

Upon acceptance of this MAEP, the following changes would be applied (they are NOT applied now):

1. **SPEC.md amendments**:
   - Add `session_id` as OPTIONAL to `query`, `follow_up`, and `context` request/response shapes.
   - Add `capabilities` object to the `server` block in `discover` response, with `sessions` boolean.
   - Add session lifecycle section (operations, cache whitelist/denylist, RBAC constraint).
   - Update §Conformance Levels to document the sessions capability.
   - Update §Access Scope & RBAC Model with explicit session-RBAC separation requirement.
   - Update `explain` response to include `session_cache_hit` and `algorithm: "session-cache-reuse"` when applicable.

2. **JSON Schema amendments** (in `schemas/`):
   - Add optional `session_id: string` to `query.request.json`, `follow_up.request.json`, `context.request.json`.
   - Add optional `session_id: string` to `query.response.json`, `follow_up.response.json`.
   - Add `capabilities` object with `sessions: boolean` to `server` block in `discover.response.json`.
   - Add `session_cache_hit: boolean` to `explain.response.json` routing decision.

These changes are a **Minor** version bump (new optional fields; no breaking changes to existing shapes).

---

## Rationale

### Why Not Sessions in Core?

The Core tier is designed for stateless-friendly, minimal implementations. A Core server can be a simple request/response handler with no durable state beyond what is needed for RBAC. Adding mandatory session lifecycle to Core would exclude this class of implementation from conformance. The hook (the `session_id` field reservation) belongs in Core because retrofitting a field name is breaking; the machinery belongs in Full because it is optional complexity.

### Why Not a New Primitive?

Session lifecycle could be a seventh primitive. It is proposed as a capability extension on existing primitives (with `session_id` threading through `query`/`follow_up`/`context`) rather than a new primitive because:
- It does not introduce a new *answer surface* — it augments existing primitives with stateful context.
- Adding a seventh primitive changes the conformance levels and the definition of Full (currently "all six primitives"). Elevating sessions to a primitive would be a more significant spec change.
- The capability-flag pattern mirrors how `schema` introspection is gated (Full), without requiring a new primitive.

### Why `capabilities.sessions` in the `server` Block?

The `server` block in `discover` is already the correct place for capability negotiation (SPEC §1, "RESOLVED (beta)"). Clients already read `server.supported_primitives` to determine what the server supports. Adding `server.capabilities.sessions` follows the same pattern and keeps capability negotiation to a single `discover` round-trip.

---

## References

- **SPEC.md §3** (`query` request/response, `answer_id` mechanism)
- **SPEC.md §4** (`follow_up`, `answer_id` reuse for cheap multi-turn)
- **SPEC.md §5** (`context`, `context.memory`, per-user state)
- **SPEC.md §Access Scope & RBAC Model** ("Re-evaluate Per-Request" requirement)
- **SPEC.md §Conformance Levels** (Core / Full / Extended definition, `server` block)
- **SPEC.md §1** (`discover` response, `server` capability block)
- **SPEC.md Design Principle 4** ("Compiled Answers Must Be Explainable")
- **MAEP-0001** (foundational primitive set; `answer_id` as core, `schema` as Full)
- **RFC-PROCESS.md** (MAEP lifecycle: Draft → Published → Under Review → Accepted)
