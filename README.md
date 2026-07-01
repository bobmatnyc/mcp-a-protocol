---
Status: DRAFT
Version: 1.1.0-beta
Date: 2026-07-01
---

# MCP-A — the MCP Answers Profile

![version](https://img.shields.io/badge/version-v1.0.1--beta-blue) ![license](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey) ![spec](https://img.shields.io/badge/spec-MCP--A-green)

**MCP-A is an MCP profile.** Every MCP-A server is an MCP server; every MCP-A client is an MCP client. MCP-A is purpose-designed around three properties -- **performance, precision, efficiency** -- so an agent gets a faster, more precise answer while the expensive client-side model does less work.

## What MCP-A Is

Raw MCP is token-expensive on the LLM side. Static tool catalogs bloat the context window; raw tool results come back unconsolidated, forcing the model to read, reconcile, and re-reason across many calls; multi-turn re-classifies every time. The LLM does the integration work, burning tokens and latency.

MCP-A moves that work server-side and hands the LLM a compiled result. Seven answer primitives are the levers: **discover** (dynamic, RBAC-filtered domain catalog replaces static tool definitions), **schema** (a domain's formal ontology -- entities, fields, types, relationships, units, allowed aggregations -- so a caller knows the shape before it queries), **query** (server classifies intent, fans out, returns one consolidated answer), **action** (executes a state-changing operation with the same RBAC-scoped, compiled-result contract), **follow_up** (drills/polls against an answer_id with no re-classification), **context** (primes identity/preferences/RBAC server-side so answers come personalized), **explain** (exposes routing/sources/confidence so the model can trust a compiled answer without re-deriving it).

The answer can come back as **structured, ontology-conformant output** -- typed objects against a domain's published schema -- not only prose. And MCP-A adds **domain ontology introspection** (the dedicated `schema` primitive) so a caller can ask what a domain's entities, fields, types, and allowed aggregations are before it queries.

Net result: fewer round-trips, smaller context, less LLM-side reasoning per answer, and precise typed values instead of prose approximations. MCP-A trades a cheap server-side model for client-side token and latency savings.

## Three Pillars: Performance, Precision, Efficiency

Three properties define MCP-A. They are the *why*.

- **Performance** -- MCP-A returns results *faster* than traditional MCP. Server-side compilation plus fewer client round-trips means lower end-to-end latency for the agent: one compiled call instead of N tool calls the model has to orchestrate and stitch.
- **Precision** -- MCP-A ensures precision in what comes back. **Aggregations** are correct server-side rollups, not LLM-estimated. **Disambiguation** (entity and term resolution) happens server-side, not guessed by the model. Structured, typed values over prose approximations.
- **Efficiency** -- MCP-A is cost-effective on the *server* side. It uses a less expensive inference model to classify, structure, and compile the response, so the expensive client-side model does less work. Cheap model structures; expensive model consumes a finished result.

## The 6 MCP-A Primitives

| # | Primitive | Responsibility |
|---|-----------|----------------|
| 1 | **discover** | "What can I ask about?" Returns a dynamic, RBAC-filtered, user-scoped catalog of *information domains* -- name, description, example questions, freshness, source systems, access scope. Optional semantic filter. Replaces static tool definitions. |
| 2 | **schema** | Return a domain's formal ontology/schema -- entities, fields, types, relationships, units, allowed aggregations -- so a caller knows the shape before it queries. The domain-introspection counterpart to `discover`; `discover` stays a thin catalog, `schema` carries the cacheable, versioned ontology surface. |
| 3 | **query** | The compiled answer. NL question → classify → fan-out → consolidated, source-cited answer. Returns answer + citations + `recommended_tool` (drill paths) + an `answer_id` handle. Supports structured-response mode when `response_schema` is supplied. |
| 4 | **follow_up** | Drill/refine against a prior `answer_id`, and poll long-running compiles. Keeps multi-turn cheap -- no re-classification. |
| 5 | **context** | Prime/inspect identity, preferences, memory, and access scope so answers are personalized and RBAC-correct. |
| 6 | **explain** | Inspect *how* an answer was compiled: routing decision, sources hit, confidence, freshness, latency, and *why* it routed that way. The trust primitive for a compiled (non-deterministic) answer -- optionally carries `feedback` to improve future routing. |

## Repository layout

What's here, and where to start:

| Path | What it is |
|------|------------|
| [`SPEC.md`](./SPEC.md) | The normative specification (v1.1.0-beta, DRAFT) — the behavior contract for the seven primitives, `schema` introspection, structured-response mode, the error model, and conformance levels. |
| [`schemas/`](./schemas/) | JSON Schema (draft 2020-12) request/response contracts for every primitive, plus shared `common.defs.json` and `error.json`. The machine-readable counterpart to `SPEC.md`. |
| [`examples/`](./examples/) | One coherent end-to-end worked scenario (request/response per step) with a narrative walkthrough. Every file validates against `schemas/`. Start here to see the profile in action. |
| [`guides/`](./guides/) | Non-normative implementer guides (complement `SPEC.md`): how to surface an underlying GraphQL/REST/SQL API beneath the seven primitives, build GraphQL queries from the `schema` ontology, and prompt LLMs for intent classification and query building. |
| [`CONFORMANCE.md`](./CONFORMANCE.md) | Checkable conformance matrix (Core / Full / Extended) and a per-primitive self-audit checklist traceable to the spec. |
| [`QUICKSTART.md`](./QUICKSTART.md) | Implementation guide: go from an existing MCP server to a conformant MCP-A server. |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | How to contribute — issues vs. MAEPs, repo layout, and PR ground rules. |
| [`RFC-PROCESS.md`](./RFC-PROCESS.md) | The MAEP (MCP-A Enhancement Proposal) governance process and publication paths. |
| [`POSITIONING.md`](./POSITIONING.md) | Naming, landscape positioning vs RAG, and relationship to MCP. |
| [`MAEP/`](./MAEP/) | MCP-A Enhancement Proposals: the MAEP process (`README.md`), the submission `TEMPLATE.md`, and filed proposals (e.g., `MAEP/0001-structured-responses-and-introspection.md`, Accepted; `MAEP/0002-session-management.md`, Draft). |

## Project Index

- **`SPEC.md`** — Formal specification (v1.1.0-beta, DRAFT). The behavior contract for the seven primitives, plus `schema` introspection and structured-response mode.
- **`schemas/`** — JSON Schema (draft 2020-12) contracts for each primitive's request/response.
- **`examples/`** — End-to-end worked scenario; every example validates against `schemas/`.
- **`CONFORMANCE.md`** — Conformance matrix and per-primitive self-audit checklist.
- **`QUICKSTART.md`** — Build your first MCP-A server.
- **`MAEP/`** — MCP-A Enhancement Proposals. `MAEP/README.md` (the process), `MAEP/TEMPLATE.md` (submission template), `MAEP/0001-structured-responses-and-introspection.md` (Accepted: the `schema` primitive and structured-response mode), and `MAEP/0002-session-management.md` (Draft: session management hook + Full-tier capability).
- **`POSITIONING.md`** — Naming, landscape positioning vs RAG, and relationship to MCP.
- **`RFC-PROCESS.md`** — How MCP-A evolves as a public standard. MAEP (MCP-A Enhancement Proposal) process model and publication paths.

## Guides

[`guides/`](./guides/) holds **non-normative** implementer guides that complement
`SPEC.md` (the normative contract). They walk through putting a real backend
behind the seven primitives:

- [`guides/surfacing-apis.md`](./guides/surfacing-apis.md) — expose an underlying GraphQL/REST/SQL API beneath MCP-A using the seven primitives as the MCP tools a client sees.
- [`guides/graphql-query-builder.md`](./guides/graphql-query-builder.md) — build a GraphQL query dynamically from a `schema` ontology response plus a parsed intent.
- [`guides/rest-api-mapping.md`](./guides/rest-api-mapping.md) — surface a REST backend: map entities/fields/relationships onto collections, projections, and sub-resources, and compute aggregations by fetching rows and reducing deterministically server-side (REST has no native aggregation).
- [`guides/sql-query-builder.md`](./guides/sql-query-builder.md) — surface a SQL warehouse (the canonical deterministic-aggregation backend): map entities→tables, fields→columns, relationships→JOINs, and allowed_aggregations→aggregate functions + GROUP BY, emitting parameterized, injection-safe SQL.
- [`guides/intent-and-query-building.md`](./guides/intent-and-query-building.md) — prompt templates for LLM intent classification, routing, and query building.

These complement the GraphQL-backed worked examples (steps 14–18), the
REST-backed examples (steps 19–22), and the SQL-backed examples (steps 23–25) in
[`examples/`](./examples/).

## Why This Exists

AI-data interfaces today are brittle. Agents call individual tools deterministically. When answers require fanout across multiple systems, classification of intent, or disambiguation of context, the burden falls on the caller to stitch it together. And when a compiled answer is non-deterministic (could come from different sources, different paths), there's no standard way to explain why it routed the way it did -- no trust.

MCP-A fixes this. It says: **If you're building a compiled-answer layer, these are the seven primitives. Here's what each one does, what it takes as input, what it returns. Here's how you route it. Here's how you explain it.**

Vendor-neutral. Publishable. Built to be a public standard from day one.

## Contributing

Changes to MCP-A go through the **MAEP** (MCP-A Enhancement Proposal) process. See [CONTRIBUTING.md](./CONTRIBUTING.md) for issues-vs-MAEPs and PR ground rules, and [RFC-PROCESS.md](./RFC-PROCESS.md) for the full governance model.

Long-term aim: graduate MCP-A into MCP's own SEP (Specification Enhancement Proposal) track at the Agentic AI Foundation, so it becomes part of the base protocol rather than a separate profile.

If you are building an MCP-A conformant server or have feedback on the spec, open an issue or a PR.

## License

Spec text is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](./LICENSE).
