---
MAEP: 0004
Title: Hierarchical and operation-aware `schema` introspection
Author: Bob Matsuoka <robert@matsuoka.com>
Status: Draft
Created: 2026-06-22
Spec-Version-Target: 1.0
---

## Summary

Extends the existing `schema` primitive so a caller can (1) **drill** into a deep
ontology a level at a time instead of receiving the whole tree at once, and (2)
introspect **operations** — enumerate the actions a domain exposes and fetch a single
action's input schema. All new fields are OPTIONAL and additive: a request that
supplies only `domain_id` behaves exactly as it does today.

---

## Motivation

`schema` today returns a domain's full ontology in one shot. That is fine for the
small, flat sales domain in the worked examples, but real domains nest — an `Order`
has `line_items`, each line item has a product, a product has a price book, and so
on. Returning the entire transitive closure on every call is wasteful (the client
pays for a tree it may never traverse) and, for large ontologies, impractical.

A caller that only needs the top-level entities should be able to ask for one level
and learn *where it can drill next*:

```json
{ "user_id": "u-4471", "domain_id": "commerce-orders", "depth": 1 }
```

→ a response describing `Order`, with `truncated: true` and
`expandable: ["order.line_items"]` — so the client knows the tree continues and
exactly where. It then drills:

```json
{ "user_id": "u-4471", "domain_id": "commerce-orders", "path": "order.line_items", "depth": 1 }
```

The second gap is operations. MAEP-0003 adds the `action` primitive, whose New
Action shape takes natural language but whose inputs are structured. A client that
wants to act *precisely* — or render a form, or validate inputs locally — needs to
know an action's input schema **before** it calls `action`. `discover` says *which
primitives* exist; it does not say *which actions a domain exposes* or *what each
one needs*. Extending `schema` to answer "what can I do here, and what does it need?"
puts operation introspection next to ontology introspection, where it belongs.

---

## Specification

*Normative. Implementations MUST conform to this section. Field definitions are in
`SPEC.md` §2 and in `schemas/schema.request.json` / `schemas/schema.response.json`.*

### 4.1 Request additions

All of the following are OPTIONAL.

| Field | Type | Meaning |
|-------|------|---------|
| `target` | `domain` \| `query` \| `action` | What to introspect. Absent ⇒ `domain` (current behavior). |
| `action_id` | string | Only meaningful when `target: action`. Present ⇒ return that action's input schema; absent ⇒ enumerate available actions. |
| `path` | string | Dotted path to a node to drill into (e.g., `order.line_items`). Absent ⇒ the root. |
| `depth` | integer (>=1) | Levels to expand from the addressed node. Default `2`. |

`domain_id` remains REQUIRED when `target` is `domain` or absent (enforced by an
`if/then` in the schema, so existing single-field requests stay valid). When
`target: action`, a server MUST interpret `action_id`'s presence per the table
above.

### 4.2 Response additions

All of the following are OPTIONAL.

| Field | Type | Meaning |
|-------|------|---------|
| `truncated` | boolean | True when deeper levels exist beyond the returned `depth`. |
| `expandable` | string[] | Node paths the client MAY drill into via a follow-up `path`. |
| `max_depth` | integer | Total depth available from the addressed node. |
| `path` | string | Echo of the node this response describes (root if the request omitted `path`). |
| `target` | `domain` \| `query` \| `action` | Echo of the request `target`. |
| `actions` | string[] | Available action names, returned when `target: action` and no `action_id` was supplied. |

To carry a single action's input schema (when `target: action` + `action_id`), the
response uses an inline JSON Schema object in `action_input_schema`. This input
schema describes the same fields an action would otherwise request **reactively**
via MAEP-0003's `clarification` rounds; exposing it here is the **proactive** path.

A server that supports drilling MUST set `truncated: true` and populate `expandable`
whenever it returns a node whose subtree it did not fully expand, so a client never
has to guess whether more exists. When the addressed node is fully expanded within
`depth`, the server MUST report `truncated: false`.

`schema` responses remain cacheable (SPEC §2); a drilled response is cacheable per
`(domain_id, target, path, depth)`.

### 4.3 Interactions with existing primitives

- **schema (existing behavior)** — a request with only `user_id` + `domain_id` is
  unchanged: `target` defaults to `domain`, `path` defaults to root, `depth` defaults
  to `2`, and the response is the same ontology shape as before (now optionally
  annotated with `truncated`/`expandable`/`max_depth`).
- **action (MAEP-0003)** — `schema(target: action)` is the **proactive** way to
  discover what an action needs. It is the counterpart to `action`'s **reactive**
  `clarification` rounds: a client MAY fetch an action's input schema up front and
  supply complete inputs on the first `action` call, avoiding a clarification
  round-trip; or it MAY skip introspection and let `action` tell it what is missing.
  Both paths MUST be supported by a Full server that exposes `action`.
- **discover** — unchanged. `discover` still advertises *which primitives* exist;
  `schema(target: action)` advertises *which actions a domain exposes*.

---

## Rationale and Alternatives

### Why extend `schema` rather than add a new primitive

Drilling and operation introspection are both "tell me about this domain's shape"
questions — the same caller intent `schema` already serves. Splitting them into new
primitives would fragment introspection across three calls and force clients to
learn three contracts for one concept. Keeping everything under `schema`, gated by an
OPTIONAL `target` discriminator, means existing clients see no change and new clients
learn one extra field.

### Why `truncated` + `expandable` instead of an opaque cursor

A cursor would let a server paginate arbitrarily, but it hides the *structure* — the
client cannot tell where in the tree it is or what its options are. `expandable`
returns concrete, addressable node paths, so the client drives drilling
deterministically and can cache each node independently. It mirrors how a file
explorer shows "this folder has children" rather than handing back a stream token.

### Why an inline input schema for actions, not a bespoke shape

Reusing inline JSON Schema (the same draft 2020-12 the rest of the repo uses, and the
same `kind: inline` notion MAEP-0001 already established for `response_schema`) means
clients already have a validator for it and can render forms or validate inputs with
zero new machinery.

### Alternatives considered

- **Always return the full tree (status quo).** Rejected for large/nested domains —
  it does not scale and wastes client tokens.
- **A separate `actions` primitive.** Rejected — see "Why extend `schema`."

---

## Backwards Compatibility

This MAEP is **additive** — a **MINOR** version bump.

- Every new request field (`target`, `action_id`, `path`, `depth`) is OPTIONAL. A
  request that sends only `domain_id` is validated and handled exactly as before;
  the `if/then` in `schema.request.json` keeps `domain_id` required for the
  `domain`/absent case so no previously-valid request becomes invalid.
- Every new response field (`truncated`, `expandable`, `max_depth`, `path`, `target`,
  `actions`, and the inline `action_input_schema`) is OPTIONAL. Existing clients that
  ignore unknown fields (SPEC §Versioning & Extension) are unaffected.
- The `schema.response` `required` set is relaxed from `["domain_id", "entities"]` to
  require `entities` only for `target` `domain`/`query` (via `if/then`). This does not
  invalidate any existing domain-ontology response — those still carry `entities` —
  but it lets a `target: action` response omit `entities` cleanly.
- No existing conformant implementation becomes non-conformant.

---

## Reference Implementation

Planned alongside MAEP-0001/0003 in the `mcp-a-spec` repo. Gotchas: a server MUST be
honest about `truncated`/`max_depth` (a client trusts these to decide whether to
drill); `expandable` paths MUST be valid `path` inputs for a subsequent request; and
RBAC still applies per `schema` call, including when enumerating actions (an action
the user cannot invoke MUST NOT appear in `actions`).

---

## Open Questions

- Should `path` use a formal pointer syntax (e.g., a constrained grammar) rather than
  dotted strings, to disambiguate entity names that contain dots?
- Should `target: query` define a distinct response shape (a queryable projection)
  beyond the ontology, or is it just a filtered view of `domain`?
- Should `action_input_schema` get a dedicated, named slot in the SPEC rather than
  riding as an inline object, once the `action` reference implementation firms up?

---

## References

- [SPEC.md](../SPEC.md) — full primitive definitions; §2 `schema`
- [MAEP-0001](./0001-structured-responses-and-introspection.md) — `schema` primitive
  and the `kind: inline` JSON Schema convention reused here
- [MAEP-0003](./0003-action-primitive.md) — the `action` primitive; this MAEP's
  `schema(target: action)` is the **proactive** discovery of an action's inputs that
  complements `action`'s **reactive** `clarification` rounds
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — MUST/SHOULD/MAY semantics
