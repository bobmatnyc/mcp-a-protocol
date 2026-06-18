# MCP-A -- the MCP Answers Profile

**Status: v1.0-beta (DRAFT)**

MCP-A is a specialization (profile) of the Model Context Protocol that returns compiled, precise, structured answers -- so the calling model does less work.  Every MCP-A server is a conformant MCP server.

---

## Why

Raw MCP hands the model a pile of unconsolidated tool results to read, reconcile, and re-reason over.  That burns tokens and round-trips.  MCP-A moves that work server-side: one compiled call, one finished answer.  The expensive client-side model consumes a typed result instead of doing the integration itself.

---

## The Three Pillars

**Performance** -- one compiled server-side call instead of N tool calls the model has to orchestrate and stitch.  Lower latency.  Fewer round-trips.

**Precision** -- server-side aggregations (correct computed rollups, not LLM-estimated), disambiguation (entity resolution server-side, not guessed), and schema-conformant structured output -- typed values against a domain's published ontology, not prose approximations.

**Efficiency** -- a cheaper server-side model classifies, structures, and compiles the response.  The expensive client model consumes a finished result.  Spend cheap server-side inference, save expensive client-side tokens and latency.

---

## The Primitives

MCP-A defines six primitives: five answer primitives (`discover`, `query`, `follow_up`, `context`, `explain`) plus **domain ontology introspection** (`schema`).  Together they enable dynamic discovery, compiled non-deterministic answers, RBAC filtering, and routing explainability -- all with structured, schema-conformant output.

See [SPEC.md](./SPEC.md) for the full request/response contracts.

| Primitive | Responsibility |
|-----------|---------------|
| `discover` | Returns a dynamic, RBAC-filtered catalog of information domains available to the authenticated user. |
| `schema` | Returns a domain's formal ontology -- entities, fields, types, relationships, and allowed aggregations -- so a caller knows what to ask for before it queries. |
| `query` | Answers a natural-language question: classifies intent, fans out to relevant sources in parallel, compiles a source-cited answer.  Supports structured-response mode when `response_schema` is supplied. |
| `follow_up` | Refines or polls a prior answer.  Reuses the prior routing decision -- multi-turn stays cheap. |
| `context` | Inspects or sets user identity, preferences, and access scope so `query` answers come back already personalized and RBAC-correct. |
| `explain` | Shows how a compiled answer was routed, why, and what alternatives were considered.  Accepts feedback to improve future routing. |

---

## Relationship to MCP

MCP standardizes how tools are called.  MCP-A standardizes how tool *results* are compiled so the LLM does less.

Every MCP-A server is a valid MCP server.  MCP-A adds a semantic layer on top: dynamic discovery, server-side compilation, RBAC filtering, and explainability -- as named primitives with typed contracts.  MCP tools (file reads, searches, API calls) become *source systems* that MCP-A fans out to and consolidates.

MCP-A is a profile of MCP, not a competitor.

---

## A Note on the Name

This is the **Compiled-Answer MCP-A** profile.  Not to be confused with:

- **MCAP** -- Foxglove's robotics log file format (`.mcap`)
- **CAG / AAG** -- Cache-Augmented Generation or Context-Augmented Generation patterns

The name MCP-A follows the same pattern as MCP itself: it is a specialization of the base protocol, suffixed to indicate the semantic layer it adds.

---

## Documents

- **[SPEC.md](./SPEC.md)** — Formal MCP-A v1.0-beta specification. The behavior contract for the six primitives, plus domain ontology/schema introspection and structured-response mode.
- **[spec/0001-initial-primitives.md](./spec/0001-initial-primitives.md)** — MAEP-0001: Accepted proposal formalizing the foundational primitive set and four resolved design decisions (dedicated `schema` primitive, tagged `response_schema` discriminator, caller-controlled `include_prose`, and Aggregation Correctness conformance).
- **[POSITIONING.md](./POSITIONING.md)** — Vendor-neutral landscape positioning. Contrasts MCP-A with RAG, cache-augmented generation, and raw MCP. Covers naming and long-term venue (AAIF/MCP SEP track).
- **[RFC-PROCESS.md](./RFC-PROCESS.md)** — MAEP (MCP-A Enhancement Proposal) governance and publication process. How changes to MCP-A are proposed, reviewed, and accepted.

---

## Contributing

Changes to MCP-A go through the **MAEP** (MCP-A Enhancement Proposal) process -- the same lightweight RFC model used by MCP itself.  See [RFC-PROCESS.md](./RFC-PROCESS.md) for the full process.

Long-term aim: graduate MCP-A into MCP's own SEP (Specification Enhancement Proposal) track at the Agentic AI Foundation, so it becomes part of the base protocol rather than a separate profile.

If you are building an MCP-A conformant server or have feedback on the spec, open an issue or a PR.

---

## License

Spec text is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](./LICENSE).
