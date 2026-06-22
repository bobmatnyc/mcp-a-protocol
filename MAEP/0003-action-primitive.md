---
MAEP: 0003
Title: The `action` primitive — write-side counterpart to `query`
Author: Bob Matsuoka <robert@matsuoka.com>
Status: Draft
Created: 2026-06-22
Spec-Version-Target: 1.0
---

## Summary

Adds the `action` primitive (a write-side counterpart to `query`): a caller asks,
in natural language, for a **state-changing** action to be taken on the user's
behalf. The service applies a tool-using model to interpret the request and either
executes immediately and reports what it did, or — if it lacks needed information —
returns what it still needs and waits for the client to supply it. Multi-turn
clarification is handled with a stable `action_id` and a `status` field. There is
**no mandatory confirm or dry-run step**.

---

## Motivation

Every primitive in MCP-A v1.0-beta is read-only. `query` compiles answers;
`schema`, `discover`, `context`, `explain`, and `follow_up` inspect or refine. But
the same value proposition that makes `query` compelling — let the server interpret
intent, resolve entities, and hand the expensive client model a finished result —
applies just as strongly to *doing* things, not only *answering* about them.

Today a client that wants to act on the user's behalf must do all the work the LLM
would otherwise offload: classify the intent, resolve which record "the Acme
renewal" refers to, decide which source-system call performs the change, and stitch
the result back. That is precisely the orchestration MCP-A exists to move
server-side.

Consider: *"Create a follow-up task for the Acme renewal due Friday."* A client
either hard-codes a create-task tool call and resolves the account itself, or it
cannot act at all. `action` lets the client express the intent in natural language
and receive a typed account of what changed:

```json
{ "request": "Create a follow-up task for the Acme renewal due Friday.", "user_id": "u-4471" }
```

→

```json
{ "action_id": "act-3b7f12", "status": "completed",
  "effects": [ { "kind": "created", "resource": "Task", "source_system": "salesforce", "entity_id": "task-88213" } ] }
```

When the service cannot proceed — say the request is *"Send the Q3 renewal proposal
to the customer"* but no recipient is known — it does not guess. It returns
`status: clarification_required` with the exact fields it needs, and the client
resumes against the same `action_id`.

---

## Specification

*Normative. Implementations MUST conform to this section. Full field definitions
are in `SPEC.md` §action and in `schemas/action.request.json` /
`schemas/action.response.json`.*

### 3.1 The `action` primitive

`action` is the write-side counterpart to `query`. A conforming server that exposes
`action` MUST list it in `discover`'s `supported_primitives`. `action` is a **Full**
conformance feature (the Core tier remains read-only — `query` + `context`).

A server MUST evaluate RBAC on every `action` call (it is never inherited or cached)
and MUST verify the user's scope **before** executing any effect. If the user lacks
permission, the server MUST return `FORBIDDEN` and MUST NOT apply any effect.

### 3.2 Request

An `action` request has two shapes, discriminated by the presence of `action_id`
(mirroring the `context` Read/Write `oneOf` pattern):

**New action** — MUST include `request` (a natural-language string) and `user_id`,
and MUST NOT include `action_id`:

```json
{
  "request": "string (natural-language state-changing request)",
  "user_id": "string (authenticated user ID)",
  "context": { "account_id": "string?", "user_preferences": "object?" },
  "options": { "timeout_seconds": "integer? (>=1, default 30)", "include_confidence": "boolean?" }
}
```

**Continuation** — MUST include `action_id`, `user_id`, and `inputs`, and MUST NOT
include `request`:

```json
{
  "action_id": "string (from a prior clarification_required response)",
  "user_id": "string (authenticated user ID)",
  "inputs": { "<field name from clarification.needed[].name>": "value", "...": "..." }
}
```

`inputs` is an open object: keys are the `name` values from the prior response's
`clarification.needed[]`. `context` and `options` MAY appear on either shape.

### 3.3 Response

The response MUST include `action_id` and `status`:

```json
{
  "action_id": "string (stable across clarification rounds; usable with explain)",
  "status": "clarification_required | completed | failed",
  "summary": "string? (human-readable account of what was done / what is needed)",
  "clarification": { "needed": [ "ClarificationField", "..." ], "prompt": "string?" },
  "result": "object | array | string | null (outcome payload, when completed)",
  "effects": [ "ActionEffect", "..." ],
  "citations": [ "Citation", "..." ],
  "error": "Error (present only when failed)",
  "routing_decision": "object? (debug/explain only)",
  "timestamp": "RFC3339 timestamp?"
}
```

- `clarification` MUST be present when and only when `status` is
  `clarification_required`. `clarification.needed` is REQUIRED and lists the fields
  (`ClarificationField`: `name`*, `description?`, `type?`, `required?`, `example?`,
  `enum?`) the client MUST supply via a continuation's `inputs`.
- `result` and `effects` describe a `completed` action. Each `ActionEffect` carries
  `kind`* (`created`/`updated`/`deleted`/`sent`/`invoked`/`other`), `resource`*,
  `source_system`*, optional `entity_id`, and optional `detail`.
- `error` MUST be present when and only when `status` is `failed`, shaped per
  `error.json`.
- `action_id` MUST be stable across clarification rounds and MUST be usable as the
  subject of an `explain` call.

### 3.4 Error codes

`action` introduces two abstract error codes (added to `error.json` and the SPEC
Error Model):

| Code | Meaning | HTTP | JSON-RPC |
|------|---------|------|----------|
| `ACTION_NOT_FOUND` | The referenced `action_id` is unknown or has expired. | 404 | -32009 |
| `ACTION_FAILED` | Execution failed at the source system. | 502 | -32010 |

Reuse existing codes where they already fit:

- `FORBIDDEN` — the user lacks permission for the requested action (RBAC denial).
- `INVALID_REQUEST` — a malformed continuation (e.g., `inputs` that do not satisfy
  the requested `clarification.needed`).
- `UNAUTHENTICATED`, `TIMEOUT` — as for other primitives.

A server MUST NOT apply any effect when it returns an error.

### 3.5 Interactions with existing primitives

- **discover** — when `action` is supported it MUST appear in
  `server.supported_primitives`.
- **schema** — the inputs an action needs are discoverable **proactively** via
  `schema(target: action, action_id: …)` (MAEP-0004), which returns the action's
  input schema *before* the client calls `action`. This is the proactive counterpart
  to `action`'s **reactive** `clarification` rounds defined here. A well-behaved
  client SHOULD prefer the proactive path to avoid an avoidable clarification
  round-trip, but a server MUST still support reactive clarification because not all
  required inputs are knowable ahead of time.
- **explain** — `action_id` is a valid subject for `explain`, so a caller can
  inspect how the service interpreted and routed a state-changing request.
- **follow_up** — `action` does **not** use `follow_up`. Continuation is its own
  shape keyed on `action_id` + `inputs`; see Rationale.

---

## Rationale and Alternatives

### Why `action` does not overload `follow_up`

`follow_up` is defined around *reusing a prior routing decision* to refine or poll a
read answer: it carries a `refinement` string or a `drill_tool_id`, and its
contract is "route once, refine for free." An action continuation is a different
operation: the client is not refining a result, it is **supplying structured inputs
the service explicitly asked for** so that a pending state change can execute.
Folding that into `follow_up` would (a) blur a read primitive into a write path,
(b) force a structured `inputs` map into a shape designed for natural-language
refinement, and (c) make RBAC reasoning harder — `follow_up` inherits the prior
answer's RBAC, whereas an action MUST re-evaluate scope and check it *before*
executing. A distinct `action_id` + `status` continuation keeps the write path
explicit and auditable.

### Why no mandatory confirm / dry-run step

A mandatory confirm step assumes the *protocol* is the right place to enforce a
human-in-the-loop policy. It is not. Whether an action needs confirmation is a
policy decision that varies by action, by deployment, and by the calling agent's
own guardrails — a destructive `delete` may warrant confirmation while a
`create task` does not. Baking a confirm round-trip into every action would tax the
common safe case to serve the rare dangerous one, and it would give a false sense of
safety (a client can always auto-confirm). Instead, the spec keeps `action`
single-purpose: interpret and execute, or ask for exactly what is missing. Clients
and deployments that want confirmation layer it on top — and a server that wants to
withhold execution can model "are you sure?" as a `clarification_required` field
(e.g., a required boolean `confirm`), which reuses the existing mechanism without a
new mandatory step.

### Alternatives considered

- **A typed `command` DSL instead of natural language.** Rejected for the New
  Action shape: it would push interpretation back to the client, defeating the
  efficiency pillar. The action's *input schema* is still available structurally via
  `schema(target: action)` for clients that want it.
- **Returning a job handle and requiring a poll for every action.** Rejected as the
  default: most actions complete synchronously. Long-running actions can still report
  progress, but forcing a poll on the common case adds latency for no benefit.

---

## Backwards Compatibility

This MAEP is **additive** — a **MINOR** version bump.

- `action` is a new primitive. Servers that do not implement it simply omit it from
  `discover`'s `supported_primitives`; clients MUST NOT call a primitive that is
  absent from that list (SPEC §1), so existing clients are unaffected.
- The two new error codes (`ACTION_NOT_FOUND`, `ACTION_FAILED`) are additions to the
  error enum; existing codes are unchanged.
- `discover.response`'s `supported_primitives` enum gains `action`; existing values
  are unchanged and existing responses remain valid.
- No existing conformant implementation becomes non-conformant.

---

## Reference Implementation

Planned alongside the MAEP-0001 reference work in the `mcp-a-spec` repo (Python
first, TypeScript bindings to follow). Known gotchas for implementers: RBAC MUST be
checked before any effect is applied; `action_id` MUST remain stable and resolvable
across clarification rounds (and afterward for `explain`); and partial execution on
`ACTION_FAILED` MUST be avoided or, where a source system cannot guarantee
atomicity, reported precisely in `effects`/`error.detail`.

---

## Open Questions

- Should `effects` ever be returned on a `failed` action to report partially-applied
  changes at a non-atomic source system, or should that always live in
  `error.detail`?
- Should there be a standard, optional `idempotency_key` on the New Action request to
  make retries safe across network failures?
- Should `action_id` expiry be bounded by the spec, or left implementation-defined as
  with `answer_id`?

---

## References

- [SPEC.md](../SPEC.md) — full primitive definitions; §action and §Error Model
- [MAEP-0001](./0001-structured-responses-and-introspection.md) — `schema` primitive
  and structured-response mode
- [MAEP-0004](./0004-hierarchical-schema.md) — hierarchical + operation-aware
  `schema`; defines the **proactive** discovery of an action's required inputs that
  complements `action`'s **reactive** `clarification` rounds
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — MUST/SHOULD/MAY semantics
