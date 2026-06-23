---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-23
---

# MCP-A Implementer Guides

> **Status: non-normative guide.** Everything in this directory is explanatory
> implementation guidance that *complements* [`../SPEC.md`](../SPEC.md). It is
> **not** part of the behavior contract. Where any guide appears to disagree
> with [`../SPEC.md`](../SPEC.md) or the [`../schemas/`](../schemas/), the SPEC
> and schemas win. None of the conventions introduced here (server-side config
> shapes, prompt templates, the illustrative builder code) are required for
> conformance; see [`../CONFORMANCE.md`](../CONFORMANCE.md) for what *is*.

These guides show how to put a real backend behind MCP-A. They use the
GraphQL-backed `storefront` domain from the worked examples
([`../examples/14-discover-graphql.*`](../examples/) through
[`../examples/18-explain-graphql.*`](../examples/)) as a running thread.

| Guide | What it covers |
|-------|----------------|
| [`surfacing-apis.md`](./surfacing-apis.md) | Expose an underlying API (GraphQL/REST/SQL) beneath MCP-A: the canonical-tools model, registering the seven primitives as MCP tools, the non-normative domain→backend binding, and an end-to-end GraphQL flow. |
| [`graphql-query-builder.md`](./graphql-query-builder.md) | Build a GraphQL query dynamically from a `schema` (ontology) response plus a parsed intent: mapping tables, the algorithm, an illustrative Python builder, and a worked query→response round-trip. |
| [`intent-and-query-building.md`](./intent-and-query-building.md) | Prompt/instruction templates for the LLMs: server-side intent classification/routing, server-side query building, and an optional client-side primitive-selection prompt — each with worked input→output. |

## Reading order

1. Read [`../SPEC.md`](../SPEC.md) §Design Principles and §Relationship to MCP
   first — these guides assume that framing.
2. [`surfacing-apis.md`](./surfacing-apis.md) — the architecture.
3. [`graphql-query-builder.md`](./graphql-query-builder.md) — the mechanism.
4. [`intent-and-query-building.md`](./intent-and-query-building.md) — the prompts
   that drive the mechanism.
