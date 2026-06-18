# Changelog

> **DRAFT spec -- API surface is beta-stable.**  Minor field changes are possible before v1.0 stable.  All changes are recorded here.

All notable changes to MCP-A are documented in this file.  Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

- **MAEP-0002** (Draft) -- session management: an OPTIONAL `session_id` hook reserved in the core `query`/`follow_up`/`context` shapes, with full session lifecycle (start/refresh/end, TTL/eviction) as a Full-tier `capabilities.sessions` extension. Proposal only; does not yet modify `SPEC.md` or the schemas.

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
- Aggregation Correctness conformance -- advertised and returned aggregations MUST be computed deterministically server-side, never LLM-estimated
- Conformance Levels -- Core / Full / Extended, declared in the `discover` `server` block
- JSON Schemas (`schemas/`, draft 2020-12) -- request/response contracts for every primitive, plus shared `common.defs.json` and `error.json`
- Worked examples (`examples/`) -- one coherent end-to-end sales-ops scenario (discover → schema → query prose → query structured → follow_up → explain → error), every file validating against the schemas
- `CONFORMANCE.md` -- checkable conformance matrix and per-primitive self-audit checklist traceable to `SPEC.md`
- `QUICKSTART.md` -- implementation guide from an existing MCP server to a conformant MCP-A server
- MAEP (MCP-A Enhancement Proposal) process for normative spec changes, with MAEP-0001 (Accepted: `schema` primitive + structured-response mode)
- CC-BY-4.0 license for all spec text and examples
