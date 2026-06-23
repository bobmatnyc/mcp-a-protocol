---
Status: DRAFT
Version: 1.0.1-beta
Date: 2026-06-18
---

# MCP-A Enhancement Proposal (MAEP) Process

A public standard evolves through community feedback and rigorous review. This document describes the **MAEP** (MCP-A Enhancement Proposal) process -- how changes to the MCP-A spec are proposed, discussed, reviewed, and accepted.

## Overview

The MAEP process is modeled on the Specification Enhancement Proposal (SEP) process used by the [Model Context Protocol](https://modelcontextprotocol.io/) and inspired by Python's PEP process. Because MCP-A is an MCP profile, MAEPs are designed to graduate into MCP's own SEP track at the AAIF/Linux Foundation when upstreamed -- the long-term home is the MCP SEP process, and the standalone `bobmatnyc/mcp-a` repo is the fast near-term path. It ensures:

- **Transparency**: All proposals are public and discoverable.
- **Community Input**: Stakeholders (tool developers, API consumers, security experts) review before adoption.
- **Traceability**: Decisions are documented with rationale.
- **Versioning**: The spec's evolution is explicit and dated.

## MAEP States

Every proposal moves through states:

```
Draft
  ↓
Published (awaiting community review)
  ↓
Under Review (public discussion, feedback)
  ↓
Accepted ← or → Rejected
  ↓
Implemented (reference implementation exists)
  ↓
Finalized (release notes + changelog)
```

## Publication Paths

### Path 1: Standalone GitHub Spec Repo (Primary)

**Repository**: `github.com/bobmatnyc/mcp-a`

**Structure**:
```
mcp-a/
├── MAEP/
│   ├── README.md (the MAEP process)
│   ├── TEMPLATE.md (submission template)
│   ├── 0001-structured-responses-and-introspection.md
│   ├── 0002-session-management.md
│   └── ...
├── SPEC.md (the normative specification)
├── README.md (links to all MAEPs)
├── RFC-PROCESS.md (this document)
├── CHANGELOG.md (releases: v0.1, v0.2, ...)
└── reference-impl/
    └── (Python/TypeScript reference implementation)
```

**Advantages**:
- Full control over MAEP process.
- Low governance overhead (no AAIF approval required).
- Faster iteration during pre-1.0 phase.
- Natural home for reference implementation.

**Disadvantages**:
- Smaller initial community (only those who discover the repo).
- May duplicate effort if a larger standard (e.g., AAIF SEP) emerges later.

**Launch Timeline**:
- **2026 Q3**: Publish v0.1 spec + first MAEPs (discovery priority, async improvements).
- **2026 Q4**: Solicit feedback from Anthropic, OpenAI, and MCP community.
- **2027 Q1**: Incorporate feedback, reach v1.0 candidate.
- **2027 Q2**: Publish v1.0 (stable, no breaking changes without major version bump).

### Path 2: MCP/AAIF SEP Track (Secondary, now more natural)

**Timeline**: Propose after v1.0-rc is stable (2027 Q1 or later).

**Process**:
1. MCP-A v1.0 is published and battle-tested.
2. Because MCP-A is an MCP profile (not a standalone protocol), the natural long-term home is the AAIF/MCP-SEP publication path: propose MCP-A as "MCP Answers Profile" and graduate the open MAEPs into MCP's own SEP track.
3. Submit to AAIF governance board.
4. AAIF reviews, possibly merges MCP-A into the MCP standard or publishes as an official MCP profile.

**Advantages**:
- Broader reach and authority.
- Natural fit as an MCP profile, not a competitor standard.
- Integration with other AAIF standards.
- Shared governance and maintenance burden.

**Disadvantages**:
- Slower review cycle.
- Must align with AAIF governance rules.
- Less autonomy over MAEP priorities.

**Strategy**: Use the standalone repo for rapid iteration and proven battle-testing. Once stable and proven, propose to AAIF/MCP as a profile and graduate MAEPs into the MCP SEP track. The standalone repo remains the fast near-term path; the MCP SEP process at AAIF/Linux Foundation is the long-term home.

---

## How to Propose a MAEP

### 1. Check Existing Proposals

Before writing, search the `mcp-a/MAEP/` directory for related MAEPs. (Avoid proposing what's already in flight.)

### 2. Draft a MAEP

Create a markdown file named `NNNN-slug-title.md` (e.g., `0003-structured-query-support.md`). Use the MAEP template below.

### 3. Open a GitHub Issue

Open an issue in the `bobmatnyc/mcp-a` repo titled "MAEP-NNNN: [Title]". Link to your draft MAEP file. Describe:
- **What** you want to change.
- **Why** (motivation).
- **How** (proposed solution sketch).
- **Open questions** (what feedback do you need?).

### 4. Discussion Phase

Community members comment on the issue. The MAEP author responds to feedback, updates the draft.

- **Duration**: At least 2 weeks (to allow async review).
- **Consensus**: Aim for broad agreement, not 100% unanimity.
- **Authority**: MCP-A spec maintainer has final say if consensus is not reached.

### 5. Finalization & Acceptance/Rejection

- **Accepted**: MAEP is merged into the `MAEP/` directory, assigned final number, marked as "Accepted".
- **Rejected**: Closed with detailed rationale. Author may reopen with new approach.

### 6. Implementation

Once accepted, the MAEP is tracked until:
- Reference implementation exists.
- At least one external implementation exists.
- Integration tests pass.

Once implemented, mark the MAEP as "Implemented" and update spec CHANGELOG.md.

---

## MAEP Template

```markdown
---
MAEP: NNNN (assigned by maintainer)
Title: [Concise title]
Author: [Your name] <email>
Status: Draft (→ Published → Under Review → Accepted → Implemented → Finalized)
Date: [YYYY-MM-DD]
Spec-Version: [e.g., 0.1 or 1.0-rc]
---

## Summary

[One sentence. What are you proposing?]

## Motivation

[Why is this change needed? What problem does it solve? What use cases does it enable?]

## Proposed Solution

[Detailed proposal. Include examples (JSON request/response shapes, markdown snippets, etc.). Link to related MAEPs or spec sections.]

## Rationale

[Why this approach over alternatives? What trade-offs did you make?]

## Backwards Compatibility

[Is this a breaking change? If so, will it require a major version bump? How will old clients behave?]

## Implementation Notes

[Guidance for implementers. Any gotchas, performance considerations, security implications?]

## Open Questions

[What feedback do you need? Are there ambiguities?]

## References

[Links to related issues, MAEPs, specs, papers, etc.]
```

---

## Versioning & Releases

MCP-A uses **semantic versioning**: MAJOR.MINOR.PATCH (e.g., 0.1.0, 1.0.0, 1.2.3), with pre-release labels (e.g., 1.0-beta) for not-yet-stable cuts.

**Current spec version: 1.0.1-beta** -- the first public beta. It is published and open for implementation and feedback; it is not yet 1.0 stable. Pre-release labels (`-beta`, `-rc`) attach to a target version under the same semver scheme. The MAEP process is unchanged: MAEPs against 1.0-beta follow the same draft → published → review → accepted → implemented flow described above.

- **MAJOR**: Breaking change to request/response shape or primitive semantics. Clients must update.
- **MINOR**: Non-breaking addition (new optional field, new primitive, new conformance level).
- **PATCH**: Bug fix, clarification, documentation.

**Release Process**:

1. MAEPs are merged and implemented.
2. Spec maintainer tags a release in git (e.g., `v1.0.0`).
3. Release notes summarize MAEPs included, any breaking changes.
4. CHANGELOG.md is updated.
5. Reference implementation is released (on PyPI, npm, etc.).

**Beta Period** (current, 1.0-beta):
- The spec is cut to 1.0-beta: published, open for implementation and feedback, but not yet stable.
- Breaking changes are still allowed during beta as feedback comes in -- they do not require full consensus while we converge on 1.0.
- At 1.0.0 stable, we commit to semantic versioning strictly: breaking changes then require a major bump and broader consensus.

---

## Governance & Decision-Making

### Spec Maintainer

**Bob Matsuoka** (Robert Matsuoka) is the initial BDFL (Benevolent Dictator For Life) for MCP-A. He:

- Assigns MAEP numbers.
- Makes final decisions if consensus is not reached.
- Maintains the spec and reference implementation.
- Represents MCP-A in discussions with other standards bodies (e.g., AAIF).

### Review Committee (Post-v1.0)

Once the community grows (10+ external implementers), establish a MCP-A Review Committee:
- 3--5 members representing diverse users (e.g., API consumer, tool developer, security expert).
- Rotate annually.
- Decisions by majority vote if the maintainer is abstaining.

### Lazy Consensus

MAEPs use **lazy consensus**: if no substantive objections after 2 weeks, the proposal is assumed accepted. This speeds iteration during the pre-1.0 phase.

Post-1.0, we may shift to **explicit consensus** (maintainer + committee explicitly vote) for more formal governance.

---

## Communication

### Official Channels

- **GitHub Issues & PRs**: Proposals and discussion.
- **Releases**: Announcements on GitHub + email to subscribers.
- **Website** (future): Static documentation site.
- **Slack** (optional): Real-time discussion for active community.

### Outside Communication

- **Papers & Talks**: Authors may present MCP-A at conferences. Link to the official spec.
- **Blog Posts**: Community members may write about MCP-A experiences. Maintainer may link from the official repo.

---

## Lifecycle of a MAEP

### Example: MAEP-0003 (Structured Query Support)

**Week 1**: Author opens GitHub issue "MAEP-0003: Add structured query support". Links to draft MAEP. Asks for feedback on the proposed JSON schema.

**Weeks 2--3**: Community comments. API consumers ask for SQL query support. Author revises the proposal to include both JSON and SQL DSLs.

**Week 4**: Maintainer reviews and comments: "I like the direction. One concern: how do we version DSLs independently from the spec?" Author updates the rationale section to address this.

**Week 5**: Author updates the MAEP with a versioning strategy (each DSL has its own version tag). Maintainer marks as "Accepted" and assigns final MAEP number (0003).

**Weeks 6--10**: Reference implementation (Python) is written and tested.

**Week 11**: A second implementation (TypeScript) is contributed by a community member.

**Week 12**: Spec maintainer merges MAEP-0003 into the spec document, updates CHANGELOG, tags release v0.2.0, and marks the MAEP as "Implemented" + "Finalized".

---

## Conflicts & Disputes

If two MAEPs propose incompatible changes, or if there's strong disagreement:

1. **Discussion Phase** (1 week): Authors and reviewers try to find a compromise.
2. **Binding Review** (1 week): Maintainer and committee (if applicable) review both proposals and issue a decision.
3. **Resolution**: One MAEP is accepted, the other rejected (with detailed rationale). The rejected author may revise and resubmit.

Appeals: If an author feels a decision was unfair, they may appeal in writing to the maintainer within 30 days. Maintainer's decision is final.

---

## FAQ

**Q: Can I propose a major new primitive (e.g., MAEP-0010 adds a 7th primitive)?**

A: Yes, via the MAEP process. But expect vigorous debate -- primitives are core to the spec. Ensure strong motivation.

**Q: What if a MAEP breaks backwards compatibility?**

A: That's allowed pre-1.0. Post-1.0, breaking MAEPs bump the major version (e.g., v1.x.x → v2.0.0) and require broader consensus.

**Q: Can the maintainer reject a MAEP unilaterally?**

A: Yes, if it's out of scope (e.g., "add machine learning routing algorithm") or conflicts with MCP-A's core principles. But the maintainer MUST explain the decision in writing.

**Q: How long until a MAEP is finalized?**

A: Typically 8--12 weeks (2 weeks discussion + 6--10 weeks implementation + testing). Simple MAEPs (clarifications, minor additions) may be finalized in 4 weeks.

**Q: What if the AAIF wants to adopt MCP-A and change the MAEP process?**

A: At that point, we'd align with AAIF governance. The current MAEP process is for the standalone era. Because MCP-A is an MCP profile, the long-term move is to graduate MAEPs into MCP's own SEP track at the AAIF/Linux Foundation -- the standalone `bobmatnyc/mcp-a` repo is the fast near-term path until then.

---

## References

- [MCP-A SPEC.md](./SPEC.md) — The specification that MAEPs modify.
- [Python PEP Process](https://www.python.org/dev/peps/pep-0001/) — Inspiration for MAEP governance.
- [MCP SEP Process](https://modelcontextprotocol.io/) — Similar standards process used by MCP.
