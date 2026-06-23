"""
Layer 1 — Schema well-formedness.

Why: Catch malformed schema files (bad $ref syntax, unknown keywords, etc.)
     before they cause cryptic validator failures during example validation.
What: Parametrize over every *.json in schemas/ that has $schema + $id;
      assert Draft202012Validator.check_schema(schema) passes without error.
Test: A deliberately broken schema (e.g., "type": 123) should fail this check.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mcpa_validation.registry import load_json


def _schema_files(schemas_dir: Path) -> list[Path]:
    return sorted(schemas_dir.glob("*.json"))


def pytest_generate_tests(metafunc):
    if "schema_path" in metafunc.fixturenames:
        schemas_dir = Path(__file__).parent.parent / "schemas"
        paths = _schema_files(schemas_dir)
        metafunc.parametrize("schema_path", paths, ids=[p.name for p in paths])


def test_schema_wellformed(schema_path: Path) -> None:
    """Assert each schema file is a valid JSON Schema draft 2020-12 document.

    Why: Malformed schemas silently pass instance validation — well-formedness
         must be checked independently.
    What: Loads the JSON file, calls Draft202012Validator.check_schema().
    Test: Run against schemas/ — all files should pass; a broken type annotation
          should raise SchemaError.
    """
    schema = load_json(schema_path)
    # Only check files that declare themselves as JSON Schema
    if "$schema" not in schema and "$id" not in schema:
        pytest.skip(f"{schema_path.name} has no $schema/$id — not a schema file")
    Draft202012Validator.check_schema(schema)
