---
Status: DRAFT
Version: 1.0-beta
Date: 2026-06-23
---

# Claude Code Guide: MCP-A Specification Repository

**MCP-A** is a specification and governance repository for the **MCP Answers Profile** — an MCP profile that moves answer compilation and routing from the LLM-side to the server-side for faster, more precise results. This is a documentation + JSON Schema + examples + proposals repository, not a code project.

## One-Paragraph Project Purpose

MCP-A defines seven answer primitives (discover, schema, query, action, follow_up, context, explain) that enable compiled-answer architectures: server-side routing and consolidation instead of client-side orchestration. It prioritizes **performance** (fewer round-trips, lower latency), **precision** (structured typed output, server-side aggregations, disambiguation), and **efficiency** (cheap server-side model + expensive client model). This repository publishes the normative SPEC, JSON Schema contracts, worked examples, and the MAEP (MCP-A Enhancement Proposal) governance process for evolving the standard.

## Project Structure

```
mcp-a-protocol/
├── README.md                          # Overview, three pillars, repo layout, contributing intro
├── SPEC.md                            # Normative specification (v1.0-beta, DRAFT) — the behavior contract
├── CONFORMANCE.md                     # Conformance matrix (Core/Full/Extended) and per-primitive audit checklist
├── QUICKSTART.md                      # Implementation guide: build a conformant MCP-A server
├── POSITIONING.md                     # Naming, landscape positioning vs RAG, relationship to MCP
├── CONTRIBUTING.md                    # Issues vs MAEPs, ground rules for PRs, maintainer info
├── RFC-PROCESS.md                     # MAEP governance process, publication paths, versioning
├── CHANGELOG.md                       # Release notes and historical changes
├── LICENSE                            # CC BY 4.0
│
├── MAEP/                              # MCP-A Enhancement Proposals (the change process)
│   ├── README.md                      # MAEP process, states, numbering, how to propose
│   ├── TEMPLATE.md                    # Submission template for new MAEPs
│   ├── 0001-structured-responses-and-introspection.md  # Accepted: schema primitive + structured mode
│   ├── 0002-session-management.md     # Draft: session hook + Full-tier capability
│   ├── 0003-action-primitive.md       # Draft: the action primitive (write-side)
│   └── 0004-hierarchical-schema.md    # Draft: hierarchical + operation-aware schema introspection
│
├── schemas/                           # JSON Schema contracts (draft 2020-12, $id-based)
│   ├── README.md                      # Schema overview, $id convention, how to validate
│   ├── common.defs.json               # Shared $defs: Citation, ClarificationField, ActionEffect, Domain, etc.
│   ├── error.json                     # Abstract error object (11 named codes: UNAUTHENTICATED, FORBIDDEN, etc.)
│   │
│   ├── discover.request.json          # Discover request schema
│   ├── discover.response.json         # Discover response (includes server capability block)
│   ├── schema.request.json            # Schema request (domain introspection, drill, action targets)
│   ├── schema.response.json           # Schema response (entities, fields, allowed_aggregations, hierarchical drilling)
│   ├── query.request.json             # Query request (prose + structured mode via response_schema)
│   ├── query.response.json            # Query response (answer, citations, structured payload, async draft)
│   ├── action.request.json            # Action request (new action vs continuation)
│   ├── action.response.json           # Action response (status, clarification, effects)
│   ├── follow_up.request.json         # Follow-up request (refinement, polling, drill)
│   ├── follow_up.response.json        # Follow-up response (status, reused_prior_routing)
│   ├── context.request.json           # Context request (read identity/preferences/RBAC OR write context)
│   ├── context.response.json          # Context response (user scope, preferences, memory)
│   ├── explain.request.json           # Explain request (inspect answer_id routing)
│   └── explain.response.json          # Explain response (routing decision, sources, confidence, feedback)
│
├── examples/                          # One coherent end-to-end worked scenario: sales-ops walkthrough
│   ├── README.md                      # Step-by-step narrative (13 steps, ~10K words with request/response shapes)
│   ├── 01-discover.{request,response}.json
│   ├── 02-schema.{request,response}.json
│   ├── 03-query-prose.{request,response}.json
│   ├── 04-query-structured.{request,response}.json
│   ├── 05-follow_up.{request,response}.json
│   ├── 06-explain.{request,response}.json
│   ├── 07-error-aggregation.{request,response}.json
│   ├── 08-query-draft.{request,response}.json
│   ├── 08-poll.{request,response}.json
│   ├── 09-action.{request,response}.json
│   ├── 10-action-clarify.{request,response}.json
│   ├── 11-action-resume.{request,response}.json
│   ├── 12-schema-drill.{request,response}.json
│   ├── 12b-schema-drill.{request,response}.json
│   └── 13-schema-action.{request,response}.json
│
└── .mcp.json                          # MCP server configuration (this repo as an MCP resource server)
```

## Authoritative-Source Hierarchy

1. **SPEC.md** (normative) — The behavior contract. All claims in other docs must trace back here.
2. **schemas/** (machine-checkable contract) — JSON Schema definitions for the seven primitives + error model. Must stay in sync with SPEC.md.
3. **examples/** (validation ground truth) — 13 worked request/response pairs. Every example MUST validate against its corresponding schema in `schemas/`.
4. **MAEP/** (change process) — How the spec evolves. All substantive changes (primitive changes, request/response shape changes, new conformance rules) go through MAEP, not direct PRs.
5. **README.md, QUICKSTART.md, POSITIONING.md** (explanatory) — Help readers understand the spec and implement it. Authoritative only for their specific domains (positioning, implementation guides).

## Critical Invariant

**Spec ⇔ Schemas ⇔ Examples must stay in sync.**

When you change a primitive's request/response shape in SPEC.md:
- Update the corresponding schema in `schemas/` (e.g., `query.request.json` and `query.response.json`).
- Update any affected example in `examples/` that uses that primitive.
- All examples MUST validate against their schemas before you commit.

**Breaking the invariant = broken spec for implementers.**

## Single-Path Workflows

### 🔴 Validate JSON Schemas are Well-Formed

**Intent**: Catch malformed schema files before they break validation.

**One command** (use **either** — pick your tool):

#### Option A: Python (jsonschema)

```bash
cd schemas
python3 << 'EOF'
import json, glob
from jsonschema import Draft202012Validator

for f in sorted(glob.glob("*.json")):
    try:
        s = json.load(open(f))
        Draft202012Validator.check_schema(s)
        print(f"✓ {f} is valid JSON Schema draft 2020-12")
    except Exception as e:
        print(f"✗ {f}: {e}")
        exit(1)
EOF
```

**Prerequisites**: `pip install jsonschema` (Python 3.8+)

#### Option B: Node (ajv-cli)

```bash
cd schemas
npx -y ajv-cli@5 compile *.json --spec=draft2020 --strict=false 2>&1 | grep -E '(error|valid)'
```

**Prerequisites**: Node 14+ (npx auto-fetches ajv-cli)

**Recommendation**: Use Python for your first-time check; it's more explicit. Use Node if you have ajv already installed locally.

---

### 🔴 Validate All Examples Against Schemas

**Intent**: Catch invalid examples before they break implementers' integrations.

**One command** (use **either**):

#### Option A: Python (jsonschema + referencing)

```bash
cd examples
python3 << 'EOF'
import json, glob, os
from referencing import Registry, Resource
from jsonschema import Draft202012Validator

# Build registry from all schema files
resources = []
for f in glob.glob("../schemas/*.json"):
    s = json.load(open(f))
    if "$id" in s:
        resources.append((s["$id"], Resource.from_contents(s)))
registry = Registry().with_resources(resources)

# Mapping: example file → schema file (from examples/README.md)
MAP = {
    "01-discover.request.json":           "../schemas/discover.request.json",
    "01-discover.response.json":          "../schemas/discover.response.json",
    "02-schema.request.json":             "../schemas/schema.request.json",
    "02-schema.response.json":            "../schemas/schema.response.json",
    "03-query-prose.request.json":        "../schemas/query.request.json",
    "03-query-prose.response.json":       "../schemas/query.response.json",
    "04-query-structured.request.json":   "../schemas/query.request.json",
    "04-query-structured.response.json":  "../schemas/query.response.json",
    "05-follow_up.request.json":          "../schemas/follow_up.request.json",
    "05-follow_up.response.json":         "../schemas/follow_up.response.json",
    "06-explain.request.json":            "../schemas/explain.request.json",
    "06-explain.response.json":           "../schemas/explain.response.json",
    "07-error-aggregation.request.json":  "../schemas/query.request.json",
    "07-error-aggregation.response.json": "../schemas/error.json",
    "08-query-draft.request.json":        "../schemas/query.request.json",
    "08-query-draft.response.json":       "../schemas/query.response.json",
    "08-poll.request.json":               "../schemas/follow_up.request.json",
    "08-poll.response.json":              "../schemas/follow_up.response.json",
    "09-action.request.json":             "../schemas/action.request.json",
    "09-action.response.json":            "../schemas/action.response.json",
    "10-action-clarify.request.json":     "../schemas/action.request.json",
    "10-action-clarify.response.json":    "../schemas/action.response.json",
    "11-action-resume.request.json":      "../schemas/action.request.json",
    "11-action-resume.response.json":     "../schemas/action.response.json",
    "12-schema-drill.request.json":       "../schemas/schema.request.json",
    "12-schema-drill.response.json":      "../schemas/schema.response.json",
    "12b-schema-drill.request.json":      "../schemas/schema.request.json",
    "12b-schema-drill.response.json":     "../schemas/schema.response.json",
    "13-schema-action.request.json":      "../schemas/schema.request.json",
    "13-schema-action.response.json":     "../schemas/schema.response.json",
}

failed = []
for ex, sch in sorted(MAP.items()):
    schema = json.load(open(sch))
    v = Draft202012Validator(schema, registry=registry)
    instance = json.load(open(ex))
    errs = list(v.iter_errors(instance))
    if errs:
        print(f"✗ {ex} -> {sch}")
        for e in errs[:3]:  # Show first 3 errors
            print(f"  {e.message} at {'.'.join(str(p) for p in e.path)}")
        failed.append(ex)
    else:
        print(f"✓ {ex} -> {sch}")

if failed:
    print(f"\n{len(failed)} example(s) failed validation. Fix and retry.")
    exit(1)
else:
    print(f"\nAll {len(MAP)} examples validated successfully.")
EOF
```

**Prerequisites**: `pip install jsonschema referencing` (Python 3.8+)

#### Option B: Node (ajv-cli)

```bash
cd examples
# Validate all examples (batch command)
npx -y ajv-cli@5 validate \
  -s ../schemas/discover.request.json \
  -r ../schemas/common.defs.json -r ../schemas/error.json \
  -d 01-discover.request.json \
  --spec=draft2020 --strict=false --validate-formats=false
# ... repeat for each example file
```

**Note**: Node/ajv requires one command per example; Python is simpler for batch validation.

**Recommendation**: Use Python. The schema/example validation is the most critical check; Python's script handles the cross-file `$ref` registry automatically.

---

### 🟡 Propose a Change (MAEP Process)

**Intent**: Evolve the spec transparently with community review.

**One-path workflow**:

1. **Check existing MAEPs** — Open `MAEP/` and `MAEP/README.md`. Is a similar proposal already in flight? (Avoid duplicate effort.)

2. **Open a GitHub issue** — Title: `MAEP: [Your proposed title]`. Describe:
   - What you want to change.
   - Why (motivation).
   - Proposed solution sketch.
   - What feedback you need.

3. **Maintainer assigns a number** — Bob Matsuoka will assign `NNNN` (e.g., `0005`).

4. **Draft your MAEP** — Copy `MAEP/TEMPLATE.md` to `NNNN-slug-title.md`. Fill every section. Open a PR linking the issue.

5. **Discussion** — Minimum 2 weeks. Community comments on the issue and PR. Lazy consensus applies: if no substantive objection, it's accepted (pre-1.0-beta only).

6. **Accepted** — MAEP is merged, status updated. Tracked to implementation.

7. **Implementation** — Reference implementation + integration tests. Once done, mark as "Implemented". When it ships in a spec release, mark as "Final" and update CHANGELOG.md.

**Key Rules**:
- **Normative changes** (primitive shape, new conformance rules, request/response fields) MUST go through MAEP. Do not land them in a drive-by PR.
- **Non-normative fixes** (typos, broken links, clarifications that don't change meaning) go straight to a PR (keep the diff small).
- **Substantive ≠ MAEP** heuristic: "Would a server that was spec-compliant yesterday become non-compliant because of this change?" → If yes, MAEP. If no, PR.

See `CONTRIBUTING.md` and `RFC-PROCESS.md` for details.

---

### 🟡 Keep CHANGELOG.md Updated

**Intent**: Record what changed, when, and why — for users and implementers.

**One-path workflow**:

1. **When a MAEP is Finalized** (merged into spec + reference implementation done + release tagged):
   - Add an entry under the new version heading in `CHANGELOG.md`.
   - Format: `## [VERSION] — YYYY-MM-DD\n\n### Added / Changed / Fixed\n- MAEP-NNNN: [Title] — brief description.`

2. **Example**:
   ```markdown
   ## [1.0-beta] — 2026-06-23

   ### Added
   - MAEP-0003: The `action` primitive — state-changing operations with clarification support.
   - MAEP-0004: Hierarchical and operation-aware `schema` introspection — drill into nested ontologies and introspect action schemas.

   ### Changed
   - Conformance levels now allow extended full-ontology introspection.

   ### Fixed
   - Typo in §Async & Polling Model.
   ```

3. **When releasing** (`git tag v1.0.0`), ensure CHANGELOG.md's top entry matches the tag version.

**Key Rules**:
- **One entry per MAEP** per version.
- **Keep it brief** — readers want to know what changed, not the full rationale.
- **Link to the MAEP** in the description (e.g., "MAEP-0003: [title]").
- **Date matters** — use the git tag date or merge date.

See `CHANGELOG.md` for the existing format; follow it exactly.

---

## Editing Conventions

### Frontmatter (required on all top-level `.md` files)

```yaml
---
Status: DRAFT | FINAL | (for specs and governance docs)
Version: 1.0-beta
Date: YYYY-MM-DD
---
```

- **Status**: `DRAFT` = open for feedback; `FINAL` = stable, released.
- **Version**: Matches git tag (e.g., `1.0-beta`, `1.0.0`). Update when spec version changes.
- **Date**: ISO 8601 (YYYY-MM-DD). Update when the doc is substantially revised.

### Markdown Style

- **Headings**: Use `#` for top-level, `##` for sections. No more than 3 levels deep unless drilling into primitives.
- **RFC 2119 Keywords**: For normative statements, use **MUST**, **SHOULD**, **MAY** (caps, bold).
- **Code blocks**: Use triple backticks with language tag (e.g., ` ```json `).
- **Links**: Always use full relative paths (e.g., `./SPEC.md#1-discover`), not bare filenames.

### Keeping Spec, Schemas, Examples in Sync

When you edit SPEC.md:

1. **Identify all affected primitives** — e.g., if you change `query` behavior, both `query.request.json` and `query.response.json` are affected.
2. **Update schemas in `schemas/`** to reflect the new request/response shape.
3. **Update examples in `examples/`** that use that primitive.
4. **Run validation** (see above) to confirm all examples still pass.
5. **Include all three in the same commit or PR** — don't split spec changes across commits if they affect the same primitive.

### PR/Commit Conventions

**Non-normative fixes** (typo, link, clarification):
- **PR title**: `docs: [what you fixed]` (e.g., `docs: fix broken link in SPEC §3`)
- **Commit message**: One sentence. `Co-Authored-By:` footer if contributing on behalf of a team.
- **Diff size**: Keep it small (< 10 lines for typos/links; < 50 lines for clarifications).

**Normative changes** (only via accepted MAEP):
- **PR title**: `MAEP-NNNN: [Title]` (e.g., `MAEP-0005: Add new context field`)
- **Commit message**: Link the MAEP issue. Include spec/schema/example changes in the same commit.
- **Diff size**: May be large; that's OK. Just be thorough.

---

## Reading Order for New Contributors

1. **README.md** — Understand the three pillars and what MCP-A is.
2. **SPEC.md (§Abstract through §Design Principles)** — Know the core principles before reading primitives.
3. **examples/README.md (§The files section only)** — See what a complete walkthrough looks like.
4. **SPEC.md (§Primitives, one at a time)** — Deep dive into each primitive's request/response.
5. **schemas/README.md** — Understand how schemas relate to SPEC text.
6. **CONTRIBUTING.md** — Know how to contribute (issues vs MAEPs).
7. **RFC-PROCESS.md** (skim) — Understand versioning and the MAEP states.

**For implementers**:
- Start with **QUICKSTART.md**.
- Reference **SPEC.md** (normative).
- Validate against **schemas/** (machine-checkable contract).
- Test using **examples/** (worked scenario).

---

## Validation Checklist

Before opening a PR, confirm:

- [ ] All SPEC.md changes have corresponding schema updates in `schemas/`.
- [ ] All affected examples in `examples/` are updated.
- [ ] All examples validate against their schemas (run the validation command).
- [ ] Frontmatter (Status, Version, Date) is consistent across related docs.
- [ ] RFC 2119 keywords (MUST, SHOULD, MAY) are used correctly in normative sections.
- [ ] Links are full relative paths (e.g., `./SPEC.md#section`) and not broken.
- [ ] If this is a normative change, a MAEP issue is open and linked.
- [ ] Commit message includes `Co-Authored-By:` footer (if using Claude Code).

---

## Key Documents

| Doc | Purpose | When to Read |
|-----|---------|--------------|
| `README.md` | Overview, high-level introduction | Start here |
| `SPEC.md` | Normative specification | Implementing or proposing changes |
| `CONFORMANCE.md` | Conformance levels (Core/Full/Extended) + audit checklist | Building a server, validating conformance |
| `QUICKSTART.md` | "Build your first MCP-A server" | Implementing |
| `CONTRIBUTING.md` | Issues vs MAEPs, ground rules | Before opening a PR |
| `RFC-PROCESS.md` | MAEP governance, versioning, publication paths | Proposing a change |
| `schemas/README.md` | Schema overview and validation techniques | Using schemas to validate implementations |
| `examples/README.md` | Worked scenario (13 steps, end-to-end) | Understanding the spec in action |
| `POSITIONING.md` | Naming, landscape positioning, vs RAG | Understanding where MCP-A fits |
| `MAEP/README.md` | MAEP process (states, numbering, how to propose) | Proposing a change |

---

## Validation & CI

A Python-based static validation suite lives in `mcpa_validation/` and `tests/`. See [`VALIDATION.md`](./VALIDATION.md) for full documentation.

**Quick commands:**
```bash
make install    # uv sync
make check      # ruff lint + full test suite (the CI gate)
make validate   # schema well-formedness + example validation only
```

CI runs automatically on every push/PR (`.github/workflows/validate.yml`).

---

## Maintenance Commands

### Quick Health Check

```bash
# Ensure schemas are well-formed
cd schemas && python3 << 'EOF'
import json, glob
from jsonschema import Draft202012Validator
for f in sorted(glob.glob("*.json")):
    s = json.load(open(f))
    Draft202012Validator.check_schema(s)
    print(f"✓ {f}")
EOF

# Ensure examples validate
cd examples && python3 << 'EOF'
# (Run the full Python validation script above)
EOF
```

### Detect Missing Schema Updates

When you edit SPEC.md, grep for the primitive names in `schemas/` to see if you missed updating a schema:

```bash
# If you changed the 'query' primitive, check:
grep -l "query" schemas/query.*.json
# Should find query.request.json and query.response.json
```

### Check for Broken Links

```bash
# Find all relative markdown links
grep -rE '\[.*\]\(\./[^)]+\)' *.md MAEP/ schemas/ examples/
# Manually verify they point to actual files (no false positives)
```

---

## Notes for Claude Code Users

**Memory**: This repository has established conventions (frontmatter format, MAEP process, validation workflow). Future Claude Code sessions will retain memory of these patterns.

**Helpful hooks** (if you set them up): `before-commit` to validate examples, `before-push` to check for broken links.

**MCP Resources**: This repo exposes itself as an MCP server (`.mcp.json`). If you have the mcp-a-protocol server configured, you can use MCP tools to query SPEC content directly.

---

## Contact & Governance

**Spec Maintainer**: Robert Matsuoka (BDFL pre-1.0; see `RFC-PROCESS.md` for post-1.0 governance).

**Contributing**: See `CONTRIBUTING.md`. Changes go through MAEP process (normative changes) or direct PRs (non-normative fixes).

**License**: CC BY 4.0. All contributions are accepted under the same license.

**Long-term vision**: Graduate MCP-A into MCP's own SEP (Specification Enhancement Proposal) track at the AAIF/Linux Foundation (see `RFC-PROCESS.md`).
