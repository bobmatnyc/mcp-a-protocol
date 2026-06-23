"""
Layer 2 — Example instance validation.

Why: Each example in examples/ is a worked reference; if it fails validation
     against its schema, implementers will build non-conformant servers.
What: Parametrize over MANIFEST; load instance + schema; collect ALL errors on
      failure and report them together (not just the first).
Test: All 31 manifest entries must validate; 07-error-aggregation.response must
      validate against error.json specifically.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcpa_validation.mapping import MANIFEST
from mcpa_validation.registry import load_json


def _manifest_ids() -> list[str]:
    return [entry[0].split("/")[-1] for entry in MANIFEST]


@pytest.mark.parametrize("example_rel,schema_name", MANIFEST, ids=_manifest_ids())
def test_example_validates(
    example_rel: str,
    schema_name: str,
    repo_root: Path,
    schemas_dir: Path,
    validator_for,
) -> None:
    """Validate a single example JSON against its designated schema.

    Why: Examples are the ground-truth reference for implementers; invalid
         examples break conformance testing and mislead implementers.
    What: Loads example_rel (relative to repo_root) and schema_name (from
          schemas_dir); runs Draft202012Validator and collects ALL errors.
    Test: Inspect the parametrize output — each line should show PASSED; any
          failure shows the full list of jsonschema ValidationError messages.
    """
    example_path = repo_root / example_rel
    schema_path = schemas_dir / schema_name

    instance = load_json(example_path)
    schema = load_json(schema_path)

    validator = validator_for(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))

    if errors:
        error_messages = "\n".join(
            f"  [{'.'.join(str(p) for p in e.path) or '<root>'}] {e.message}"
            for e in errors
        )
        pytest.fail(
            f"{example_rel} failed validation against {schema_name}:\n{error_messages}"
        )
