# MCP-A Worked Example — A Sales-Ops Walkthrough

This directory is one coherent end-to-end scenario that flows through the whole MCP-A
profile. A sales-operations analyst (`user_id: u-4471`) wants to understand this quarter's
pipeline and ARR. We follow them through every primitive — discovery, schema introspection,
a prose answer, a structured answer, a cheap follow-up, a routing explanation, one error, and
an async draft-then-poll round.

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
| 8 | `08-query-draft.request.json` / `08-query-draft.response.json` | `query` (draft) | [§Async & Polling Model](../SPEC.md#async--polling-model) | `query.request.json` / `query.response.json` |
| 8 | `08-poll.request.json` / `08-poll.response.json` | `follow_up` (poll) | [§Async & Polling Model](../SPEC.md#async--polling-model) | `follow_up.request.json` / `follow_up.response.json` |
| 9 | `09-action.request.json` / `09-action.response.json` | `action` (one-shot) | [§7](../SPEC.md#7-action) | `action.request.json` / `action.response.json` |
| 10 | `10-action-clarify.request.json` / `10-action-clarify.response.json` | `action` (clarify) | [§7](../SPEC.md#7-action) | `action.request.json` / `action.response.json` |
| 11 | `11-action-resume.request.json` / `11-action-resume.response.json` | `action` (resume) | [§7](../SPEC.md#7-action) | `action.request.json` / `action.response.json` |
| 12 | `12-schema-drill.request.json` / `12-schema-drill.response.json`, `12b-schema-drill.request.json` / `12b-schema-drill.response.json` | `schema` (drill) | [§2](../SPEC.md#2-schema) | `schema.request.json` / `schema.response.json` |
| 13 | `13-schema-action.request.json` / `13-schema-action.response.json` | `schema` (`target: action`) | [§2](../SPEC.md#2-schema) | `schema.request.json` / `schema.response.json` |
| 14 | `14-discover-graphql.request.json` / `14-discover-graphql.response.json` | `discover` | [§1](../SPEC.md#1-discover) | `discover.request.json` / `discover.response.json` |
| 15 | `15-schema-graphql.request.json` / `15-schema-graphql.response.json` | `schema` | [§2](../SPEC.md#2-schema) | `schema.request.json` / `schema.response.json` |
| 16 | `16-query-graphql-structured.request.json` / `16-query-graphql-structured.response.json` | `query` (structured) | [§3 Structured-Response Mode](../SPEC.md#structured-response-mode) | `query.request.json` / `query.response.json` |
| 17 | `17-action-graphql.request.json` / `17-action-graphql.response.json` | `action` (GraphQL mutation) | [§7](../SPEC.md#7-action) | `action.request.json` / `action.response.json` |
| 18 | `18-explain-graphql.request.json` / `18-explain-graphql.response.json` | `explain` | [§6](../SPEC.md#6-explain) | `explain.request.json` / `explain.response.json` |

Steps 14–18 are a second, GraphQL-backed thread that accompanies the
[implementer guides](../guides/README.md): a `storefront` commerce domain whose
single source system is `storefront-graphql`. They show discovery, ontology
introspection, a structured revenue rollup with server-side aggregations, an
`action` that maps to a GraphQL mutation, and an `explain` over the query's
answer. The query issues `answer_id` `ans-graphql-7a1f` (threaded into the
step-18 `explain`); the action issues `action_id` `act-graphql-2c8e`. See
[`../guides/surfacing-apis.md`](../guides/surfacing-apis.md) for the end-to-end
walkthrough and [`../guides/graphql-query-builder.md`](../guides/graphql-query-builder.md)
for how step 16's GraphQL query is built from step 15's ontology.

The `answer_id` issued in step 3 (`ans-7c41a8`) is threaded through steps 5 and 6 — the
follow-up refines it, and explain inspects it. Step 8 runs a separate async round on its own
`answer_id` (`ans-c08d51`): a draft `query` issues the handle, and a polling `follow_up` reuses
it to fetch the completed result. That is the multi-turn story: one expensive routing decision,
reused cheaply.

Steps 9–13 extend the same analyst's session to the write side and to deeper introspection.
Steps 9–11 exercise the **`action`** primitive (MAEP-0003): a one-shot completed action, then a
two-turn clarify→resume round that threads a single `action_id` (`act-9c2a55`) through both calls.
Steps 12–13 exercise the hierarchical and operation-aware **`schema`** extensions (MAEP-0004):
depth-limited drilling into a nested ontology, and `target: action` introspection of what a
domain can *do*.

---

## Step 1 — `discover`: what can I ask about?

**SPEC [§1](../SPEC.md#1-discover) · schema `discover.{request,response}.json`**

The analyst's client opens the session by asking what is available, scoped to the user's
permissions. The request carries the authenticated `user_id` and an optional
`semantic_filter`.

The response leads with the **`server` capability block** — `mcp_a_version`,
`conformance_level`, and `supported_primitives`. This server declares `Full`, so all seven
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

## Step 8 — async draft → poll: don't block on a long compile

**SPEC [§Async & Polling Model](../SPEC.md#async--polling-model) · schema `query.{request,response}.json` then `follow_up.{request,response}.json`**

Some questions take real time to compile — here, eight quarters of YoY ARR growth by region and
segment with churn netted out, hitting the data warehouse. Rather than block, the analyst opts in
to the async path with `options.draft: true`. The server returns immediately with a **partial
answer**, `is_draft: true`, and a fresh `answer_id` (`ans-c08d51`).

The client then **polls** by issuing a `follow_up` against that same `answer_id` (no `refinement`,
no `drill_tool_id` — a bare poll). When the compile has finished, the `follow_up` response returns
the completed result with `is_draft: false`, `status: "complete"`, the final per-region/per-segment
citations, and `routing_decision.reused_prior_routing: true` (the in-flight compile was finalized,
not re-routed). A still-pending poll would instead return the cached draft with `is_draft: true`
and `status: "pending"`. This is the **Async-Friendly** principle (SPEC Design Principle 6): clients
never block on compilation.

Note `is_draft` is OPTIONAL on a `query` response (absent ⇒ `false`); steps 3–4 omit it because
they are normal complete answers, and only the draft answer here carries `is_draft: true`.

## Step 9 — `action`: do something, one shot

**SPEC [§7](../SPEC.md#7-action) · schema `action.{request,response}.json`**

The analyst stops asking and starts acting: *"Create a follow-up task for the Acme renewal due
Friday."* The `action` request carries the natural-language `request`, the `user_id`, and an
`account_id` in `context`. The service interprets the intent, resolves "the Acme renewal" to
`acct-acme-001` and "Friday" to a concrete date, creates the task, and returns
`status: "completed"` with a fresh **`action_id` (`act-3b7f12`)**, a `result` payload, and an
**`effects`** array recording the `created` `Task` at `salesforce`. There is no confirm step —
the write happened in one compiled call. RBAC was checked before the effect was applied.

## Step 10 — `action`: not enough info → `clarification_required`

**SPEC [§7](../SPEC.md#7-action) · schema `action.{request,response}.json`**

A vaguer request: *"Send the Q3 renewal proposal to the customer."* The service cannot safely
guess who the customer is or where to send the proposal, so instead of inventing a recipient it
returns `status: "clarification_required"` with a new **`action_id` (`act-9c2a55`)** and a
**`clarification.needed`** list — `account_id` and `recipient_email` (both required) and an
optional `delivery` field with an `enum`. Each entry is a `ClarificationField` whose `name` is the
key the client must echo back. This is the **reactive** path to discovering an action's inputs;
step 13 shows the **proactive** path via `schema(target: action)`.

## Step 11 — `action`: resume with the same `action_id`

**SPEC [§7](../SPEC.md#7-action) · schema `action.{request,response}.json`**

The client supplies what was asked for. The continuation request carries the **same `action_id`
(`act-9c2a55`)** plus an **`inputs`** map keyed by the field names from step 10's
`clarification.needed` (`account_id`, `recipient_email`, `delivery`). The service now has
everything it needs: it sends the proposal and returns `status: "completed"` with a `sent` `email`
effect. The stable `action_id` is what ties the two turns into one logical action — and it remains
usable as the subject of an `explain` call.

## Step 12 — `schema` (drill): expand one level at a time

**SPEC [§2](../SPEC.md#2-schema) · schema `schema.{request,response}.json`**

Some ontologies nest too deeply to return whole. Against a `commerce-orders` domain, the client
asks for `depth: 1`. The response describes the `Order` entity and its top-level fields, then
signals that the tree continues: **`truncated: true`**, **`expandable: ["order.line_items"]`**, and
**`max_depth: 3`**. The client drills with a second request (`12b`) that sets
**`path: "order.line_items"`**, and the response returns the `LineItem` shape with
`truncated: false`. `truncated`/`expandable`/`max_depth` let the client traverse a large schema
deterministically and cache each node on its own — no opaque cursor required.

## Step 13 — `schema` (`target: action`): introspect what a domain can *do*

**SPEC [§2](../SPEC.md#2-schema) · schema `schema.{request,response}.json`**

Finally the analyst asks what *actions* the `salesforce-crm` domain exposes and what one of them
needs, using **`target: "action"`**. The response enumerates the available **`actions`**
(`create_task`, `send_proposal`, `update_opportunity_stage`) and returns the `create_task` input
schema in **`action_input_schema`** — an inline JSON Schema listing `title`, `account_id`,
`due_date` (all required) and an optional `assignee`. This is the **proactive** counterpart to
step 10's reactive clarification: a client can fetch the input schema up front and supply complete
`inputs` on its first `action` call, skipping a clarification round-trip.

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
    "08-query-draft.request.json":        "query.request.json",
    "08-query-draft.response.json":       "query.response.json",
    "08-poll.request.json":               "follow_up.request.json",
    "08-poll.response.json":              "follow_up.response.json",
    "09-action.request.json":             "action.request.json",
    "09-action.response.json":            "action.response.json",
    "10-action-clarify.request.json":     "action.request.json",
    "10-action-clarify.response.json":    "action.response.json",
    "11-action-resume.request.json":      "action.request.json",
    "11-action-resume.response.json":     "action.response.json",
    "12-schema-drill.request.json":       "schema.request.json",
    "12-schema-drill.response.json":      "schema.response.json",
    "12b-schema-drill.request.json":      "schema.request.json",
    "12b-schema-drill.response.json":     "schema.response.json",
    "13-schema-action.request.json":      "schema.request.json",
    "13-schema-action.response.json":     "schema.response.json",
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
