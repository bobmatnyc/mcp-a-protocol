# Changelog

> **DRAFT spec -- API surface is beta-stable.**  Minor field changes are possible before v1.0 stable.  All changes are recorded here.

All notable changes to MCP-A are documented in this file.  Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

Nothing yet.

---

## [1.0-beta] - 2026-06-18

### Added

- `discover` primitive -- enumerate available answer domains exposed by a server
- `schema` primitive -- domain ontology and schema introspection; returns structured type definitions for a named domain so callers can validate queries before sending them
- `query` primitive -- primary question-answering call; returns compiled, structured answers with `response_schema`-tagged object output and a `prose` control flag (see MAEP-0001)
- `follow_up` primitive -- refine or extend a prior query result within the same session context
- `context` primitive -- attach or retrieve session-scoped background that shapes subsequent query results
- `explain` primitive -- request a plain-language account of how a returned answer was derived
- Performance pillar -- defines latency and throughput expectations for compliant servers
- Precision pillar -- defines answer fidelity, citation, and structured-output contract
- Efficiency pillar -- defines token budget and round-trip minimization expectations for the calling model
- MAEP (MCP-A Enhancement Proposal) process for normative spec changes
- CC-BY-4.0 license for all spec text and examples
