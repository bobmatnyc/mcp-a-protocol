---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-18
---

# Contributing to MCP-A

MCP-A is built to be a public standard. Contributions are welcome — from typo fixes to new
primitives — but substantive changes go through a lightweight governance process so the spec
evolves transparently and traceably.

## Issues vs. MAEPs

**Open a GitHub issue** for:

- Bugs in the spec, schemas, examples, or docs (typos, broken links, a schema that doesn't
  match `SPEC.md`).
- Questions, clarifications, and "is this intended?" discussion.
- Early-stage ideas you want feedback on before drafting a formal proposal.

**Open a MAEP (MCP-A Enhancement Proposal)** for any **substantive change to the spec** — new
or changed primitives, request/response shape changes, new conformance requirements, new
error codes, or anything that changes the behavior contract. MAEPs are how the standard
changes; don't land substantive spec changes via a drive-by PR.

The full governance model — MAEP states, the template, lazy consensus, versioning, and the
path to the MCP SEP track at the AAIF/Linux Foundation — lives in
[`RFC-PROCESS.md`](./RFC-PROCESS.md). In short:

1. Search [`spec/`](./spec/) for related MAEPs first (don't duplicate what's in flight).
2. Draft a MAEP file `NNNN-slug-title.md` using the template in `RFC-PROCESS.md`.
3. Open an issue titled `MAEP-NNNN: [Title]` linking your draft; discuss for ≥ 2 weeks.
4. On acceptance, the MAEP is merged into [`spec/`](./spec/) and assigned a final number.

Breaking changes are allowed during the `1.0-beta` period; post-1.0 they require a major
version bump and broader consensus (see `RFC-PROCESS.md` §Versioning).

## Repository layout

| Path | What it is |
|------|------------|
| [`SPEC.md`](./SPEC.md) | The normative specification — the behavior contract for the six primitives, `schema` introspection, structured-response mode, the error model, and conformance levels. |
| [`schemas/`](./schemas/) | JSON Schema (draft 2020-12) contracts for every primitive's request/response, plus shared `common.defs.json` and `error.json`. The machine-readable counterpart to `SPEC.md`. |
| [`examples/`](./examples/) | One coherent end-to-end worked scenario (request/response per step) with a narrative `README.md`. Every file validates against `schemas/`. |
| [`spec/`](./spec/) | Accepted MAEPs (e.g., `0001-initial-primitives.md`). |
| [`CONFORMANCE.md`](./CONFORMANCE.md) | Checkable conformance matrix and per-primitive self-audit checklist. |
| [`QUICKSTART.md`](./QUICKSTART.md) | Implementation guide: build a conformant MCP-A server. |
| [`POSITIONING.md`](./POSITIONING.md) | Naming, landscape positioning, relationship to MCP and RAG. |
| [`RFC-PROCESS.md`](./RFC-PROCESS.md) | The MAEP governance process. |

## Ground rules for PRs

- **Keep spec, schemas, and examples in sync.** If you change a request/response shape in
  `SPEC.md`, update the corresponding schema in `schemas/` and any affected example in
  `examples/` in the same PR.
- **Examples must validate.** Run the validation harness in
  [`examples/README.md`](./examples/README.md#validating-these-examples) before opening a PR;
  every example must pass against its schema.
- **Match the existing tone** — measured, contract-first, RFC 2119 keywords (MUST / SHOULD /
  MAY) for normative statements.

## License

By contributing, you agree your contributions are licensed under
[CC BY 4.0](./LICENSE), the same as the spec text.
