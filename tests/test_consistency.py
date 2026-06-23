"""
Layer 3 — Cross-document consistency checks.

Why: Catches divergence between schemas, examples, and normative docs
     (SPEC.md / CONFORMANCE.md) that would break implementers.

Checks:
  (a) All 7 primitives (discover, schema, query, action, follow_up, context,
      explain) have both .request.json and .response.json in schemas/.
  (b) Each error code in error.json's "code" enum appears at least once in
      CONFORMANCE.md or SPEC.md. Any code not found is a hard CI failure —
      this detects real spec/schema drift that must be resolved before merge.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcpa_validation.registry import load_json

PRIMITIVES = [
    "discover",
    "schema",
    "query",
    "action",
    "follow_up",
    "context",
    "explain",
]

# Derived at collection time from error.json so drift is caught automatically.
_ERROR_CODES = load_json(
    Path(__file__).parent.parent / "schemas" / "error.json"
)["properties"]["code"]["enum"]


def test_error_codes_non_empty() -> None:
    """Guard against an empty extraction making the parametrized layer vacuously pass.

    Why: If _ERROR_CODES is empty (e.g. schema structure changed), all
         parametrized test_error_code_appears_in_spec_or_conformance cases
         would simply not run, giving a false green.
    What: Asserts _ERROR_CODES has exactly 11 entries matching the known enum.
    Test: Change error.json to remove the 'code' enum and this test fails.
    """
    assert len(_ERROR_CODES) == 11, (
        f"Expected 11 error codes in error.json, got {len(_ERROR_CODES)}: {_ERROR_CODES}"
    )


def test_all_primitives_have_request_and_response_schemas(schemas_dir: Path) -> None:
    """Assert each of the 7 MCP-A primitives has .request.json + .response.json.

    Why: A missing schema file means a whole primitive is unvalidatable — a
         serious gap that must surface immediately.
    What: Checks schemas_dir for {primitive}.request.json and
          {primitive}.response.json for each of the 7 primitives.
    Test: Remove a schema file from schemas/ and this test fails.
    """
    missing: list[str] = []
    for primitive in PRIMITIVES:
        for suffix in ("request.json", "response.json"):
            expected = schemas_dir / f"{primitive}.{suffix}"
            if not expected.exists():
                missing.append(str(expected))

    if missing:
        pytest.fail(
            "Missing schema files for primitives:\n  " + "\n  ".join(missing)
        )


def _get_error_codes(schemas_dir: Path) -> list[str]:
    """Load the 'code' enum values from error.json.

    Why: Shared helper for loading the authoritative error code list from the
         schema so callers don't duplicate JSON traversal logic.
    What: Reads error.json from schemas_dir and returns the 'code' enum list.
    Test: Pass schemas_dir and assert the returned list is non-empty.
    """
    error_schema = load_json(schemas_dir / "error.json")
    return error_schema["properties"]["code"]["enum"]


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("code", _ERROR_CODES)
def test_error_code_appears_in_spec_or_conformance(code: str, repo_root: Path) -> None:
    """Assert each error code from error.json appears in SPEC.md or CONFORMANCE.md.

    Why: Error codes that exist in the schema but are undocumented in the spec
         create confusion for implementers and indicate spec/schema drift.
         A missing code must break CI so drift cannot be silently merged.
    What: Loads SPEC.md and CONFORMANCE.md text; asserts the code string
          appears in at least one of the two documents.
    Test: The 11 current codes all appear in SPEC.md error model section.
          Remove one from SPEC.md and CONFORMANCE.md to confirm this fails.
    """
    spec_text = _load_text(repo_root / "SPEC.md")
    conformance_text = _load_text(repo_root / "CONFORMANCE.md")

    combined = spec_text + conformance_text
    if code not in combined:
        pytest.fail(
            f"Error code '{code}' not found in SPEC.md or CONFORMANCE.md. "
            "This is a real spec/schema divergence that must be resolved before merge."
        )
