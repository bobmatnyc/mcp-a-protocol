---
Status: DRAFT
Version: 1.1.0-beta
Date: 2026-07-01
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

The MAEP process is documented in [`MAEP/README.md`](./MAEP/README.md); the submission
template is at [`MAEP/TEMPLATE.md`](./MAEP/TEMPLATE.md). The full governance model — MAEP
states, lazy consensus, versioning, and the path to the MCP SEP track at the AAIF/Linux
Foundation — lives in [`RFC-PROCESS.md`](./RFC-PROCESS.md). In short:

1. Search [`MAEP/`](./MAEP/) for related MAEPs first (don't duplicate what's in flight).
2. Copy [`MAEP/TEMPLATE.md`](./MAEP/TEMPLATE.md) to `NNNN-slug-title.md` in `MAEP/`.
3. Open an issue titled `MAEP-NNNN: [Title]` linking your draft; discuss for ≥ 2 weeks.
4. On acceptance, the MAEP is merged into [`MAEP/`](./MAEP/) and assigned a final number.

A MAEP is the right vehicle for anything that touches the seven primitives, the three pillars,
or the structured-response contract. Typos, broken links, and plain-language clarifications
that don't change normative meaning can go directly to a PR — keep the diff small and
describe what you changed.

Breaking changes are allowed during the `1.0-beta` period; post-1.0 they require a major
version bump and broader consensus (see `RFC-PROCESS.md` §Versioning).

## Repository layout

| Path | What it is |
|------|------------|
| [`SPEC.md`](./SPEC.md) | The normative specification — the behavior contract for the seven primitives, `schema` introspection, structured-response mode, the error model, and conformance levels. |
| [`schemas/`](./schemas/) | JSON Schema (draft 2020-12) contracts for every primitive's request/response, plus shared `common.defs.json` and `error.json`. The machine-readable counterpart to `SPEC.md`. |
| [`examples/`](./examples/) | One coherent end-to-end worked scenario (request/response per step) with a narrative `README.md`. Every file validates against `schemas/`. |
| [`MAEP/`](./MAEP/) | The MAEP process (`README.md`), submission `TEMPLATE.md`, and filed proposals (e.g., `0001-structured-responses-and-introspection.md` (Accepted), `0002-session-management.md` (Draft)). |
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

See [`VALIDATION.md`](./VALIDATION.md) for how to run the validation suite (`make check`) before opening a PR.

## Conduct

Be direct and be civil. Critique the spec, not the person.

## Maintainer and governance

Robert Matsuoka has final say on all changes prior to v1.0 stable. The goal is to move to a
wider review body and the AAIF/MCP-SEP track as the spec matures — so good proposals will
shape that future process (see [`RFC-PROCESS.md`](./RFC-PROCESS.md)).

## License

All contributions are accepted under **CC BY 4.0** ([LICENSE](./LICENSE)), the same as the
spec text. By submitting a PR you confirm that you have the right to license your
contribution under those terms.
