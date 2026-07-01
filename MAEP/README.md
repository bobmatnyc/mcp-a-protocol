# MCP-A Enhancement Proposals (MAEP)

This directory contains the MAEP process documentation and all filed proposals.

---

## What is a MAEP?

A **MAEP** (MCP-A Enhancement Proposal) is the mechanism for proposing normative
changes to the MCP-A spec.  Not every change needs one -- typos, broken links, and
non-normative clarifications go straight to a PR or issue.  A MAEP is needed when
you are changing what a conforming implementation MUST, SHOULD, or MAY do: adding
or modifying a primitive, changing a request/response shape, defining new
conformance rules, or altering versioning semantics.

When in doubt: if a server that was spec-compliant yesterday could become
non-compliant tomorrow because of your change, file a MAEP.

---

## States

Every MAEP moves through a defined lifecycle:

```
Draft
  |
  v
Under Review  (public discussion open, at least 2-week window)
  |
  +---> Rejected  (closed with written rationale; author may resubmit)
  |
  v
Accepted
  |
  v
Implemented  (reference implementation exists and integration tests pass)
  |
  v
Final  (included in a released spec version; CHANGELOG updated)
```

**Withdrawn** is a terminal state the author may invoke at any point before Accepted.

---

## How to Propose

### 1. Check what exists

Search the `MAEP/` directory for related proposals.  Open GitHub issues with the
`maep` label are also in-flight -- read them before filing a duplicate.

### 2. Open a GitHub issue

Title it `MAEP: [Your proposed title]`.  Describe what you want to change, why,
and your proposed solution sketch.  Ask explicitly for the feedback you need.
The maintainer will assign a four-digit number.

### 3. Draft your MAEP

Copy `TEMPLATE.md` to `NNNN-your-slug.md` in this directory, where `NNNN` is the
assigned number (zero-padded to four digits).  Fill in every section.  Open a PR
linking to the issue.

### 4. Discussion

Community members comment on the issue and PR.  Update the draft in response to
substantive feedback.  The review window is **at least two weeks** to allow async
participation across time zones.

**Lazy consensus applies during the pre-1.0 phase**: if no substantive objection
is raised within two weeks, the proposal is assumed accepted and moves to the next
state.  The maintainer may extend the window for proposals with broad impact.

### 5. Decision

**Robert Matsuoka** (BDFL, pre-1.0) makes the final call when consensus is not
reached.  The decision is written into the MAEP and the GitHub issue is closed
with a summary.

- Accepted: MAEP is merged, status updated, tracked to implementation.
- Rejected: Closed with a written rationale.  Author may revise and resubmit.

### 6. Implementation and Final

Once accepted, the MAEP is tracked until:

- A reference implementation exists.
- Integration tests pass against it.

At that point the MAEP is marked **Implemented**.  When it ships in a spec release
it becomes **Final** -- the CHANGELOG is updated and the spec version is tagged in
git.

---

## Numbering

Numbers are zero-padded to four digits and assigned by the maintainer after the
issue is filed: `0001`, `0002`, and so on.  Do not self-assign a number in your
draft -- use `XXXX` as a placeholder until the maintainer assigns one.

---

## Versioning tie-in

MCP-A uses semantic versioning (MAJOR.MINOR.PATCH).  Accepted and Implemented
MAEPs roll into the next spec version according to the change type:

| Change type | Version bump |
|-------------|-------------|
| Breaking change to primitive semantics or request/response shape | MAJOR |
| Non-breaking addition (new optional field, new primitive, new conformance level) | MINOR |
| Clarification or bug fix with no behavioral change | PATCH |

During the **1.0-beta** phase, breaking changes are still allowed without a major
bump -- we are converging on 1.0, not locked.  At 1.0 stable, semver is strict.

---

## Relationship to MCP

MCP-A is a profile of the Model Context Protocol.  MAEPs are designed with
graduation in mind: when MCP-A reaches 1.0 stable and is ready to be proposed as
an official MCP profile, open MAEPs will be re-filed into MCP's own SEP track at
the Agentic AI Foundation (AAIF).

The standalone `mcp-a-spec` repo is the fast path for pre-1.0 iteration.  The MCP
SEP process at AAIF is the long-term home.

---

## Index

| MAEP | Title | Status |
|------|-------|--------|
| [0001](./0001-structured-responses-and-introspection.md) | Domain introspection (`schema`) and structured-response mode | Accepted |
| [0002](./0002-session-management.md) | Session management — Core hook + Full-tier capability | Draft |
| [0003](./0003-action-primitive.md) | The `action` primitive — write-side counterpart to `query` | Draft |
| [0004](./0004-hierarchical-schema.md) | Hierarchical and operation-aware `schema` introspection | Draft |
| [0005](./0005-compiled-query-assistance.md) | Compiled Query Assistance — API-surface schema, query-building discover, and query clarification | Draft |
