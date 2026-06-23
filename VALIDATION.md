---
Status: DRAFT
Version: 1.0.1-beta
Date: 2026-06-23
---

# MCP-A Validation & CI

This document describes the Python-based static validation suite for the MCP-A specification repository. The suite validates JSON Schemas and worked examples programmatically, and runs in CI on every push/PR.

## Quick Start

```bash
make install   # uv sync — installs all dependencies
make check     # ruff lint + full pytest suite (the CI gate)
make validate  # narrower: schema well-formedness + example validation only
```

## Test Layers

| Layer | File | What it checks |
|-------|------|----------------|
| 1 | `test_schemas_wellformed.py` | Every `schemas/*.json` file is a valid JSON Schema draft 2020-12 document (`Draft202012Validator.check_schema`) |
| 2 | `test_examples_validate.py` | Every example in the manifest validates against its designated schema (using an offline `$id`-keyed registry) |
| 2 gate | `test_examples_manifest_complete.py` | Every `examples/*.json` file is present in the manifest — a new example without a manifest entry fails CI |
| 3 | `test_consistency.py` | (a) All 7 primitives have `.request.json` + `.response.json`; (b) each error code in `error.json` appears in `SPEC.md` or `CONFORMANCE.md` |
| 4 | `test_conformance_traceability.py` | Every `SPEC §...` citation in `CONFORMANCE.md` resolves to a real heading in `SPEC.md` |

## How the Registry Works

MCP-A schemas use absolute `$id`-based cross-file `$ref`s of the form `https://mcp-a.dev/schemas/common.defs.json#/$defs/Citation`. This namespace is **not a live URL** — it is a logical identifier.

`mcpa_validation/registry.py:build_registry()` iterates `schemas/*.json`, reads each file's `"$id"` field, and registers it as a `referencing.Resource` keyed by that URI. When `Draft202012Validator` resolves a `$ref`, it looks up the URI in this registry instead of making a network request.

## Adding a New Example

1. Add the JSON file to `examples/` (e.g., `examples/14-new-primitive.request.json`).
2. Add a corresponding entry to `MANIFEST` in `mcpa_validation/mapping.py`:
   ```python
   ("examples/14-new-primitive.request.json", "new-primitive.request.json"),
   ```
3. Run `make validate` to confirm the new example passes.
4. Commit both the example and the manifest update together.

The `test_examples_manifest_complete.py` gate will fail CI if step 2 is skipped.

## Make Targets

| Target | Command | Purpose |
|--------|---------|---------|
| `install` | `uv sync` | Install all dependencies (production + dev) |
| `validate` | `pytest` Layers 1+2 | Fast schema/example check |
| `test` | `uv run pytest` | Full test suite |
| `lint` | `uv run ruff check .` | Lint all Python files |
| `format` | `uv run ruff format .` | Auto-format Python files |
| `check` | lint + test | The gate CI calls |
