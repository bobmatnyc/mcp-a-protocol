# MCP-A JSON Schemas

Machine-readable JSON Schema definitions for the **MCP-A (MCP Answers Profile)** protocol,
v1.0-beta. These schemas are the machine-readable counterpart to [`../SPEC.md`](../SPEC.md)
and define the request/response contract for each of the six primitives.

## Draft version

All schemas use **JSON Schema draft 2020-12**
(`"$schema": "https://json-schema.org/draft/2020-12/schema"`).

## `$id` convention

Every schema has a stable, dereferenceable `$id` of the form:

```
https://mcp-a.dev/schemas/<filename>.json
```

Cross-file references use absolute `$id`-based `$ref`s into the shared definitions file, e.g.:

```json
{ "$ref": "https://mcp-a.dev/schemas/common.defs.json#/$defs/Citation" }
```

The `$id` is a logical identifier, not a guarantee of a live HTTP endpoint; resolve refs
from this directory using a schema registry (see "How to validate" below).

## Files

### Shared

| File | Purpose |
|------|---------|
| `common.defs.json` | Reusable `$defs`: `Citation`, `Domain`, `AccessScope`, `RoutingDecision`, `ResponseSchemaTarget`, `Error`. Referenced by the primitive schemas via `$ref`. |
| `error.json` | The standalone abstract error object. `code` is an `enum` of exactly the nine named codes from SPEC §Error Model. |

### Primitives (request + response per primitive)

| Primitive | Request | Response |
|-----------|---------|----------|
| 1. discover  | `discover.request.json`  | `discover.response.json` (includes the required `server` capability block) |
| 2. schema    | `schema.request.json`    | `schema.response.json` (domain ontology; per-field `allowed_aggregations`) |
| 3. query     | `query.request.json`     | `query.response.json` (covers prose **and** structured-response mode) |
| 4. follow_up | `follow_up.request.json` | `follow_up.response.json` (query shape + polling `status`) |
| 5. context   | `context.request.json`   | `context.response.json` |
| 6. explain   | `explain.request.json`   | `explain.response.json` |

`context.request.json` is a `oneOf` of two shapes — a **Read** request and a **Write**
request — discriminated by the presence of `action` (Write has it; Read forbids it).

### Examples

| File | Purpose |
|------|---------|
| `examples/query.response.structured.example.json` | A real structured-mode `query` response payload (from SPEC §3). Validates against `query.response.json`. |

## Notable contract details

- **discover.response** — `server` block is **required** with `mcp_a_version`,
  `conformance_level` (enum `Core` / `Full` / `Extended`), and `supported_primitives[]`.
- **query.response** — `answer_id` and `citations` are required; `is_draft` is OPTIONAL
  (absent ⇒ `false`, i.e. a complete answer) and appears `true` only on a draft/partial answer.
  `structured` + `structured_schema_ref` appear only in structured-response mode.
- **query.request** — `response_schema` uses the tagged `ResponseSchemaTarget` discriminator
  (`kind` ∈ `schema_ref` | `domain` | `inline`); `kind` constrains the type of `value`.
- **error** — `code` enum is exactly: `UNAUTHENTICATED`, `FORBIDDEN`, `INVALID_REQUEST`,
  `DOMAIN_NOT_FOUND`, `ANSWER_NOT_FOUND`, `SCHEMA_NONCONFORMANT`, `AGGREGATION_NOT_ALLOWED`,
  `TIMEOUT`, `SOURCE_UNAVAILABLE`.
- Optional (`?`-marked) spec fields are **not** in `required`; MUST-fields are `required`.
- `additionalProperties: false` is set on closed object shapes. Open maps
  (`access_scope`, `preferences`, `memory`, `source_latencies`, `confidence_per_source`,
  and inline `structured` payloads) intentionally allow additional properties, consistent
  with the spec's extension model ("clients SHOULD ignore unknown fields").

## How to validate

### Python (`jsonschema`)

```bash
pip install jsonschema referencing
```

```python
import json, glob
from referencing import Registry, Resource
from jsonschema import Draft202012Validator

# Build a registry from all schema files for cross-file $ref resolution
resources = []
for f in glob.glob("*.json"):
    s = json.load(open(f))
    resources.append((s["$id"], Resource.from_contents(s)))
registry = Registry().with_resources(resources)

# Well-formedness
for _id, res in resources:
    Draft202012Validator.check_schema(res.contents)

# Validate an instance
schema = json.load(open("query.response.json"))
v = Draft202012Validator(schema, registry=registry)
instance = json.load(open("examples/query.response.structured.example.json"))
errors = list(v.iter_errors(instance))
assert not errors, errors
```

### Node (`ajv-cli`)

```bash
npx -y ajv-cli@5 validate \
  -s query.response.json \
  -r common.defs.json -r error.json \
  -d examples/query.response.structured.example.json \
  --spec=draft2020 --strict=false --validate-formats=false
```

> `--strict=false` disables ajv's opinionated strict-mode warnings (union types,
> unknown `format`). The schemas are valid draft 2020-12; `format` is treated as an
> annotation per spec default. `--validate-formats=false` skips format assertion.
