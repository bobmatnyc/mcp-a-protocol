# MCP-A Worked Example — A Sales-Ops Walkthrough

This directory is one coherent end-to-end scenario that flows through the whole MCP-A
profile. A sales-operations analyst (`user_id: u-4471`) wants to understand this quarter's
pipeline and ARR. We follow them through every primitive — discovery, schema introspection,
a prose answer, a structured answer, a cheap follow-up, a routing explanation, and one error.

Every request/response file here validates against the JSON Schemas in
[`../schemas/`](../schemas/) (see [Validating these examples](#validating-these-examples)).
The domain is a neutral `salesforce-crm` sales domain — no internal company specifics.

## The files

| Step | Files | Primitive | SPEC | Schema |
|------|-------|-----------|------|--------|
| 1 | `01-discover.request.json` / `01-discover.response.json` | `discover` | [§1](../SPEC.md#1-discover) | `discover.request.json` / `discover.response.json` |
| 2 | `02-schema.request.json` / `02-schema.response.json` | `schema` | [§2](../SPEC.md#2-schema) | `schema.request.json` / `schema.response.json` |
| 3 | `03-query-prose.request.json` / `03-query-prose.response.json` | `query` (prose) | [§3](../SPEC.md#3-query) | `query.request.json` / `query.response.json` |
| 4 | `04-query-structured.request.json` / `04-query-structured.response.json` | `query` (structured) | [§3 Structured-Response Mode](../SPEC.md#structured-response-mode) | `query.request.json` / `query.response.json` |
| 5 | `05-follow_up.request.json` / `05-follow_up.response.json` | `follow_up` | [§4](../SPEC.md#4-follow_up) | `follow_up.request.json` / `follow_up.response.json` |
| 6 | `06-explain.request.json` / `06-explain.response.json` | `explain` | [§6](../SPEC.md#6-explain) | `explain.request.json` / `explain.response.json` |
| 7 | `07-error-aggregation.request.json` / `07-error-aggregation.response.json` | `query` → error | [§Error Model](../SPEC.md#error-model) | `query.request.json` / `error.json` |

The `answer_id` issued in step 3 (`ans-7c41a8`) is threaded through steps 5 and 6 — the
follow-up refines it, and explain inspects it. That is the multi-turn story: one expensive
routing decision, reused cheaply.

---

## Step 1 — `discover`: what can I ask about?

**SPEC [§1](../SPEC.md#1-discover) · schema `discover.{request,response}.json`**

The analyst's client opens the session by asking what is available, scoped to the user's
permissions. The request carries the authenticated `user_id` and an optional
`semantic_filter`.

The response leads with the **`server` capability block** — `mcp_a_version`,
`conformance_level`, and `supported_primitives`. This server declares `Full`, so all six
primitives (including structured mode) are on the table. A client should read this block
*before* relying on structured mode rather than probing each primitive (SPEC §1, §Conformance
Levels). The `domains` array is RBAC-filtered: only domains `u-4471` can see appear, each with
its `freshness_seconds` so the client can decide whether the data is fresh enough to ask.

We will work in the `salesforce-crm` domain.

## Step 2 — `schema`: what is the shape before I query?

**SPEC [§2](../SPEC.md#2-schema) · schema `schema.{request,response}.json`**

Before asking for typed output, the client introspects the chosen domain's ontology. The
response describes two entities — `Account` and `Opportunity` — their fields and types, the
relationship between them, and, critically, the **`allowed_aggregations` per field**.

Those `allowed_aggregations` are the contract for structured mode. They list only the
rollups the domain computes deterministically server-side (SPEC §Aggregation Correctness).
Note that `Account.arr` allows `sum`, `avg`, `min`, `max`, `count`, but
`Opportunity.probability` allows only `avg`, `min`, `max` — *not* `sum`, because summing
probabilities is not a meaningful deterministic rollup. That distinction is what makes step 7
fail by design.

## Step 3 — `query` (prose mode): the compiled answer

**SPEC [§3](../SPEC.md#3-query) · schema `query.{request,response}.json`**

The analyst asks a natural-language question: *"How is our open pipeline looking for this
quarter, and where is the risk?"* No `response_schema` is supplied, so this is prose mode.
The request sets `include_confidence: true`.

The server classifies the question, fans out to the domain's source systems, consolidates,
and returns a single compiled `answer` with `citations` (each carrying at least a
`source_system`, plus a `snippet` and a `confidence` because we asked). It also returns the
**`answer_id` `ans-7c41a8`** — the handle we reuse in steps 5 and 6 — and a
`recommended_tool` drill path pointing at the `sales-activity` domain. The model receives one
finished answer instead of orchestrating and stitching N raw tool calls.

## Step 4 — `query` (structured mode): typed values, server-side aggregation

**SPEC [§3 Structured-Response Mode](../SPEC.md#structured-response-mode) · schema `query.{request,response}.json`**

Now the analyst wants precise numbers, not prose. The request asks *"Total ARR and active
account count by region for active accounts"* and supplies a tagged `response_schema`:

```json
"response_schema": { "kind": "domain", "value": "salesforce-crm" }
```

The `kind` discriminator (`schema_ref` | `domain` | `inline`) tells the server how to
interpret `value`; here it targets the `salesforce-crm` ontology introspected in step 2.

The response returns the authoritative payload in `structured` — one typed object per region
with a **server-side `sum` of `arr` and `count` of active accounts** — plus
`structured_schema_ref: "salesforce-crm"`. Because `include_prose: true`, a short prose
`answer` rides along as a summary, but `structured` is the source of truth. The aggregations
are computed, not LLM-estimated (SPEC §Aggregation Correctness) — and `sum`/`count` on
`Account.arr`/`account_id` are exactly what step 2's schema declared allowed. Citations are
still present, as required for structured payloads.

## Step 5 — `follow_up`: refine cheaply, no re-routing

**SPEC [§4](../SPEC.md#4-follow_up) · schema `follow_up.{request,response}.json`**

The analyst drills into the prose answer from step 3 by referencing its `answer_id`
(`ans-7c41a8`) with a `refinement`: *"Narrow to AMER only, and just the negotiation-stage
deals at risk."*

This is a pure narrowing of the prior result. The response's `routing_decision` reports
`reused_prior_routing: true` — no new source fan-out happened; the prior result set was
filtered post-hoc by region and stage. The `answer_id` is unchanged (refinement, not a new
compile), `status: "complete"`, and a fresh `recommended_tool` points at the four quiet deals.
This is the **Cheap Multi-Turn** principle: route once, refine for free.

## Step 6 — `explain`: how and why it routed

**SPEC [§6](../SPEC.md#6-explain) · schema `explain.{request,response}.json`**

To trust a non-deterministic compiled answer, the analyst inspects the routing for
`ans-7c41a8`. The response shows `question_classified_as`, `domains_considered` vs.
`domains_queried` (it considered `sales-activity` but did not query it), and a
`routing_decision` with a human-readable `rationale` plus **`alternative_routings` with
scores** — including the road not taken (fanning out to `sales-activity`) and why it scored
lower. It returns `source_latencies` and `confidence_per_source` so the client can judge
answer quality without recomputing it. The request also carried `feedback`; the response
acknowledges it with `feedback_recorded: true`.

## Step 7 — an error: `AGGREGATION_NOT_ALLOWED`

**SPEC [§Error Model](../SPEC.md#error-model) · schema `error.json`**

Finally, the analyst asks for a structured rollup the schema forbids: *"the sum of win
probability ... by region."* Step 2's schema declared `Opportunity.probability` as
`avg`/`min`/`max` only. A structured query requesting `sum` on it cannot conform, so the
server fails cleanly per the **abstract error taxonomy** rather than guessing.

The error response is shaped per `error.json`: a named abstract `code`
(`AGGREGATION_NOT_ALLOWED`), a human-readable `message`, and a `detail` object naming the
offending domain, entity, field, requested aggregation, and the allowed set. Per SPEC §Error
Model, the implementer maps this abstract code to the transport's native encoding (HTTP `400`,
JSON-RPC `-32006`); clients should branch on the abstract `code` name, not the numeric code.

---

## Validating these examples

Every file in this directory validates against its schema in [`../schemas/`](../schemas/):
request files against `*.request.json`, response files against `*.response.json`, and the
step-7 error response against `error.json`. Cross-file `$ref`s into `common.defs.json` resolve
through a registry.

### Python (`jsonschema` + `referencing`)

```bash
pip install jsonschema referencing
```

```python
import json, glob, os
from referencing import Registry, Resource
from jsonschema import Draft202012Validator

resources = []
for f in glob.glob("schemas/*.json"):
    s = json.load(open(f))
    if "$id" in s:
        resources.append((s["$id"], Resource.from_contents(s)))
registry = Registry().with_resources(resources)

MAP = {
    "01-discover.request.json":           "discover.request.json",
    "01-discover.response.json":          "discover.response.json",
    "02-schema.request.json":             "schema.request.json",
    "02-schema.response.json":            "schema.response.json",
    "03-query-prose.request.json":        "query.request.json",
    "03-query-prose.response.json":       "query.response.json",
    "04-query-structured.request.json":   "query.request.json",
    "04-query-structured.response.json":  "query.response.json",
    "05-follow_up.request.json":          "follow_up.request.json",
    "05-follow_up.response.json":         "follow_up.response.json",
    "06-explain.request.json":            "explain.request.json",
    "06-explain.response.json":           "explain.response.json",
    "07-error-aggregation.request.json":  "query.request.json",
    "07-error-aggregation.response.json": "error.json",
}

for ex, sch in sorted(MAP.items()):
    schema = json.load(open(os.path.join("schemas", sch)))
    v = Draft202012Validator(schema, registry=registry)
    instance = json.load(open(os.path.join("examples", ex)))
    errs = list(v.iter_errors(instance))
    assert not errs, (ex, errs)
    print("PASS", ex, "->", sch)
```

### Node (`ajv-cli`)

```bash
# Example: validate the structured query response
npx -y ajv-cli@5 validate \
  -s schemas/query.response.json \
  -r schemas/common.defs.json -r schemas/error.json \
  -d examples/04-query-structured.response.json \
  --spec=draft2020 --strict=false --validate-formats=false
```
