# Changelog

> **DRAFT spec -- API surface is beta-stable.**  Minor field changes are possible before v1.0 stable.  All changes are recorded here.

All notable changes to MCP-A are documented in this file.  Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

- **MAEP-0002** (Draft) -- session management: an OPTIONAL `session_id` hook reserved in the core `query`/`follow_up`/`context` shapes, with full session lifecycle (start/refresh/end, TTL/eviction) as a Full-tier `capabilities.sessions` extension. Proposal only; does not yet modify `SPEC.md` or the schemas.
- **MAEP-0003** (Draft) -- the `action` primitive: a write-side counterpart to `query` that takes a state-changing action on the user's behalf from a natural-language `request`. Returns `action_id` + `status` (`clarification_required` | `completed` | `failed`); multi-turn via `action_id` + `inputs` continuation, with reactive `clarification` rounds. No mandatory confirm/dry-run step. Adds the `action` primitive to `SPEC.md` (§7), `action.request.json`/`action.response.json` schemas, `ClarificationField`/`ActionEffect` in `common.defs.json`, the `ACTION_NOT_FOUND` (HTTP 404 / JSON-RPC `-32009`) and `ACTION_FAILED` (HTTP 502 / JSON-RPC `-32010`) error codes, `action` in `discover`'s `supported_primitives`, and examples 09–11. Additive (**MINOR**); Full-tier (Core stays read-only). Primitive count six → seven.
- **MAEP-0004** (Draft) -- hierarchical and operation-aware `schema`: OPTIONAL, additive controls on the `schema` primitive for drilling a deep ontology a level at a time (`target`, `path`, `depth` request fields; `truncated`, `expandable`, `max_depth`, `path`, `target` response fields) and for operation introspection (`target: action` enumerates a domain's `actions` or returns one action's input schema). The required inputs for an `action` (MAEP-0003) are thus discoverable proactively via `schema(target: action)` as well as reactively via clarification. Updates `SPEC.md` §2 and the `schema.request.json`/`schema.response.json` schemas, and adds examples 12/12b/13. Additive (**MINOR**); a request with only `domain_id` is unchanged.

---

## [1.1.0-beta] - 2026-07-01

### Added
- MAEP-0005: Compiled Query Assistance — three additive, Full-tier, off-by-default-for-Core capabilities that let the server assist in constructing and repairing queries while keeping every primitive shape stable:
  - `discover` **query-building guidance** — OPTIONAL `natural_language_guidance`, `query_templates`, and `disambiguation_hints` on each domain entry (fixed-shape, bounded; SHOULD be auto-derived from backend metadata). Adds `QueryTemplate`/`DisambiguationHint` `$defs` and extends `Domain` in `common.defs.json`; SPEC §1; example 01.
  - `schema` **`api_surface`** — OPTIONAL backend-surface transparency (`format` ∈ `openapi-3.1`/`graphql-sdl`/`sql-catalog`/`other`, inline or reference `spec`), supplementary to the primary ontology. `schema.response.json`; SPEC §2; example 02.
  - `query` **clarification** — OPTIONAL `status: clarification_required` + `clarification` object (reusing `action`'s `ClarificationField`) with a `query_id` + `clarification_inputs` continuation; the server SHOULD infer/repair before falling back to clarification and reserve `INVALID_REQUEST` for genuinely unparseable input. `query.request.json`/`query.response.json`; SPEC §3, §Terminology; new example 26.

### Changed
- Spec version bumped to 1.1.0-beta (MINOR, additive) across documentation frontmatter and titles. No breaking changes; every existing conformant implementation remains conformant.

---

## [1.0.1-beta] - 2026-06-23

### Added
- Conformance/validation test suite: JSON Schema meta-validation, example-against-schema validation, a manifest-completeness gate, spec↔schema↔conformance consistency checks, and conformance↔SPEC traceability — wired into GitHub Actions and a `make check` target (uv + pytest + jsonschema/referencing + ruff).
- Non-normative implementer guides under `guides/`: surfacing underlying APIs through the seven canonical primitives; GraphQL, REST, and SQL backend mapping with dynamic query builders; and intent-classification / query-building prompt templates.
- Worked, schema-valid examples 14–25 for a GraphQL-backed (`storefront`), REST-backed (`support-desk`), and SQL-backed (`analytics-warehouse`) domain.

### Changed
- Version coordinate bumped to 1.0.1-beta across documentation and the `mcp_a_version` value in the discover examples. No normative SPEC text or JSON Schema changes.

---

## [1.0-beta] - 2026-06-18

### Added

- `discover` primitive -- enumerate available answer domains exposed by a server, leading with a `server` capability block (`mcp_a_version`, `conformance_level`, `supported_primitives`) for single-round-trip capability negotiation
- `schema` primitive -- domain ontology and schema introspection; returns structured type definitions for a named domain so callers can validate queries before sending them
- `query` primitive -- primary question-answering call; returns compiled, source-cited answers with structured-response mode when a tagged `response_schema` is supplied, plus caller-controlled prose via `options.include_prose` (see MAEP-0001)
- `follow_up` primitive -- refine or extend a prior query result, or poll a long-running compile, reusing the prior routing decision
- `context` primitive -- attach or retrieve user identity, preferences, memory, and access scope that shape subsequent query results
- `explain` primitive -- request a plain-language account of how a returned answer was routed, with alternative routings, per-source latency/confidence, and feedback capture
- Performance pillar -- defines latency and throughput expectations for compliant servers
- Precision pillar -- defines answer fidelity, citation, and structured-output contract
- Efficiency pillar -- defines token budget and round-trip minimization expectations for the calling model
- Error Model -- an abstract error taxonomy (`UNAUTHENTICATED`, `FORBIDDEN`, `INVALID_REQUEST`, `DOMAIN_NOT_FOUND`, `ANSWER_NOT_FOUND`, `SCHEMA_NONCONFORMANT`, `AGGREGATION_NOT_ALLOWED`, `TIMEOUT`, `SOURCE_UNAVAILABLE`) with canonical HTTP and JSON-RPC transport mappings
- JSON-RPC error codes locked: the numeric JSON-RPC values `-32001`–`-32008` mapped to the abstract error codes (§Error Model) are **normative for v1.0-beta** (previously an open first cut). A conformant JSON-RPC binding MUST use exactly these values; the assignment is revisable only via the MAEP process.
- Aggregation Correctness conformance -- advertised and returned aggregations MUST be computed deterministically server-side, never LLM-estimated
- Conformance Levels -- Core / Full / Extended, declared in the `discover` `server` block
- JSON Schemas (`schemas/`, draft 2020-12) -- request/response contracts for every primitive, plus shared `common.defs.json` and `error.json`
- Worked examples (`examples/`) -- one coherent end-to-end sales-ops scenario (discover → schema → query prose → query structured → follow_up → explain → error), every file validating against the schemas
- `CONFORMANCE.md` -- checkable conformance matrix and per-primitive self-audit checklist traceable to `SPEC.md`
- `QUICKSTART.md` -- implementation guide from an existing MCP server to a conformant MCP-A server
- MAEP (MCP-A Enhancement Proposal) process for normative spec changes, with MAEP-0001 (Accepted: `schema` primitive + structured-response mode)
- CC-BY-4.0 license for all spec text and examples
