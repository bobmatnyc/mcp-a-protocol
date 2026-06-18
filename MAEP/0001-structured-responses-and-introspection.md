---
MAEP: 0001
Title: Domain introspection (`schema`) and structured-response mode
Author: Robert Matsuoka <robert@matsuoka.com>
Status: Accepted
Created: 2026-06-18
Spec-Version-Target: 1.0-beta
---

## Summary

Adds the `schema` primitive (primitive #2) for domain ontology introspection, and
extends `query` with a `response_schema` field and an `options.include_prose` control so callers can
request typed, schema-conformant output instead of -- or in addition to -- prose
approximations.

---

## Motivation

MCP-A's core value proposition is **precision**: typed, server-aggregated answers
that callers can act on without re-parsing prose.  Without a dedicated introspection
primitive, a caller has no reliable way to know what entities, fields, units, or
aggregations a domain server supports.  That leaves two bad options:

1. Hardcode assumptions about domain shape in the client -- fragile, breaks silently
   when servers evolve.
2. Ask a `query` and infer the schema from the answer -- ambiguous and inconsistent
   across servers.

The same gap exists on the response side.  A raw `query` today returns prose.
Callers that want structured data must parse natural language output, which defeats
the purpose of a typed protocol.

This MAEP closes both gaps:

- `schema` gives callers a machine-readable ontology they can use to formulate
  correct `query` requests and validate responses.
- `response_schema` on `query` lets callers request a typed response in a shape
  they declare or reference -- turning MCP-A into a precision data API, not just a
  Q&A layer.

---

## Specification

*Normative.  Implementations MUST conform to this section.  Full field definitions
are in `SPEC.md`; this section records the decisions made here.*

### 2.1  The `schema` primitive

`schema` is primitive #2 in the MCP-A set (after `discover`, before `query`).

A `schema` request asks a server to return its domain ontology for a named domain:

```json
{
  "user_id": "u_123",
  "domain_id": "hospitality.revenue",
  "include_aggregations": true,
  "include_relationships": true
}
```

The request carries the authenticated `user_id` (the server MUST enforce domain
access scope) and the `domain_id` to introspect.  `include_aggregations` and
`include_relationships` are optional booleans (both default `true`) that let a
caller trim the response.

A conforming server MUST return an object containing:

| Field | Type | Description |
|-------|------|-------------|
| `entities` | array | Named entity types in the domain (e.g., `hotel`, `segment`, `date_range`) |
| `fields` | map | Per-entity field definitions: name, type, unit, nullable |
| `relationships` | array | Edges between entities (e.g., `hotel` has-many `segments`) |
| `allowed_aggregations` | array | Aggregation functions the server supports (e.g., `sum`, `avg`, `percentile`) |
| `units` | map | Canonical unit definitions referenced in `fields` |

A server MAY return additional extension fields under a namespaced key.

A server MUST return a 404-equivalent error if the requested domain is not served.

`schema` responses are cacheable.  Servers SHOULD include a `schema_version` string
so callers can detect ontology changes without re-fetching unconditionally.

### 2.2  `response_schema` on `query`

`query` gains an optional `response_schema` field.  When present, the server MUST
return a `structured` field in the response containing data conformant to the
declared schema.

`response_schema` is a tagged object with a required `kind` discriminator and a
`value` payload:

```json
{ "kind": "schema_ref", "value": "OccupancyBySegment" }
{ "kind": "domain",     "value": "hotel.segment_summary" }
{ "kind": "inline",     "value": { /* JSON Schema object */ } }
```

`value` is interpreted according to `kind`: for `schema_ref` it is a registered
schema name (string), for `domain` it is a `domain_id` (string), and for `inline`
it is an inline JSON Schema definition (object).  Clients MUST inspect `kind` to
interpret `value`.  This `kind`/`value` form is the single canonical wire shape — it
is what `SPEC.md` defines and what the `schemas/` (`ResponseSchemaTarget` in
`common.defs.json`) validate and the `examples/` use.

**Unknown kind/value**: if the server does not recognize a `schema_ref` or `domain`
`value`, it MUST return HTTP 422 (Unprocessable Entity) with an error body
identifying the unknown name.  Servers MUST NOT silently fall back to prose for an
explicitly requested schema.

### 2.3  `include_prose` control on `query`

`query` gains an optional `options.include_prose` field — a boolean that defaults
to `true`:

| Value | Meaning |
|-------|---------|
| `true` | (default) Server returns a prose `answer` summary alongside structured data |
| `false` | Server omits the prose `answer` entirely |

```json
{ "options": { "include_prose": false } }
```

When `response_schema` is supplied:

- The `structured` field in the response is REQUIRED and authoritative.
- `include_prose` defaults to `true`; set it to `false` to suppress the prose
  `answer`.
- The `structured` field MUST conform to the declared schema; the prose SHOULD
  summarize the same data.  Where they conflict, `structured` is the ground truth.

When `response_schema` is absent, `include_prose` defaults to `true` and
`structured` MAY be omitted.

---

## Rationale and Alternatives

### Why a dedicated `schema` primitive instead of folding into `discover`?

`discover` answers "what domains does this server serve and how do I reach them?"
-- it is a registry primitive.  `schema` answers "what is the shape of data in
this domain?" -- it is an ontology primitive.  Folding them together conflates two
distinct caller intents and bloats the `discover` response with data most callers
do not need on every call.  Separate primitives keep each call cheap and
independently cacheable.

### Why a tagged discriminator on `response_schema` instead of duck-typing?

Duck-typing (e.g., "if it has a `$schema` key, treat it as inline") produces
ambiguous edge cases and makes error messages worse.  A required `kind` field makes
the intent explicit, lets servers produce actionable 422 errors with the exact
unknown name, and makes client-side validation straightforward.  Keeping a single
`kind`/`value` shape (no bare-string shorthand) means there is exactly one wire form
to implement and validate against, which is why `SPEC.md`, the schemas, and the
examples all use it verbatim.

### Why `include_prose: false` instead of just omitting a prose field?

Explicit opt-out signals intent.  A server that sees `include_prose: false` knows
the caller does not want prose and MUST NOT include it -- saving tokens and
bandwidth on high-volume analytical calls.  Without an explicit signal, a server
cannot distinguish "caller forgot to ask for prose" from "caller does not want
prose."

---

## Backwards Compatibility

This MAEP is **additive**.  All new fields (`response_schema`,
`options.include_prose`) are optional on `query`.  Existing `query` calls that do
not include these fields
behave identically to pre-0001 behavior -- servers return prose, no `structured`
field is expected or required.

The `schema` primitive is new.  Servers that do not implement it MUST return an
appropriate error (e.g., unknown primitive).  Callers SHOULD handle that error
gracefully and fall back to hardcoded schema assumptions if needed.

No existing conformant implementation becomes non-conformant as a result of this
MAEP.

---

## Reference Implementation

**duetto-intelligence** (internal, in progress as of 2026-06-18).  Implements
`schema` for the `hospitality.revenue` domain and the `response_schema` /
`options.include_prose` extensions on `query`.

A public Python reference implementation is planned for the `mcp-a-spec` repo
alongside the 1.0-beta spec publication.  TypeScript bindings to follow.

---

## Open Questions

None open at Accepted status.  Resolved questions during the pre-acceptance
discussion:

- **Should `schema_version` be required?**  No -- SHOULD is sufficient.  Servers
  without versioned ontologies should not be blocked from conformance.
- **Should `type: inline` support JSON Schema draft-07 only?**  No -- the spec
  references JSON Schema without pinning a draft.  Servers MUST document which
  draft they validate against.

---

## References

- [SPEC.md](../SPEC.md) -- full primitive definitions for `discover`, `query`,
  `follow_up`, `context`, `explain`
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) -- MUST/SHOULD/MAY keyword
  semantics
- [JSON Schema](https://json-schema.org/) -- schema format for `type: inline`
