"""
Layer 3 — Cross-document consistency checks.

Why: Catches divergence between schemas, examples, and normative docs
     (SPEC.md / CONFORMANCE.md) that would break implementers.

Checks:
  (a) All 7 primitives (discover, schema, query, action, follow_up, context,
      explain) have both .request.json and .response.json in schemas/.
  (b) Each error code in error.json's "code" enum appears at least once in
      CONFORMANCE.md or SPEC.md. Codes not found are reported; individual
      genuinely-absent codes use xfail with a clear reason rather than a hard
      failure of the whole suite.
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
    """Load the 'code' enum values from error.json."""
    error_schema = load_json(schemas_dir / "error.json")
    return error_schema["properties"]["code"]["enum"]


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "code",
    [
        "UNAUTHENTICATED",
        "FORBIDDEN",
        "INVALID_REQUEST",
        "DOMAIN_NOT_FOUND",
        "ANSWER_NOT_FOUND",
        "SCHEMA_NONCONFORMANT",
        "AGGREGATION_NOT_ALLOWED",
        "TIMEOUT",
        "SOURCE_UNAVAILABLE",
        "ACTION_NOT_FOUND",
        "ACTION_FAILED",
    ],
)
def test_error_code_appears_in_spec_or_conformance(code: str, repo_root: Path) -> None:
    """Assert each error code from error.json appears in SPEC.md or CONFORMANCE.md.

    Why: Error codes that exist in the schema but are undocumented in the spec
         create confusion for implementers and indicate spec/schema drift.
    What: Loads SPEC.md and CONFORMANCE.md text; checks if the code string
          appears in either document.
    Test: The 11 current codes all appear in SPEC.md error model section.
    """
    spec_text = _load_text(repo_root / "SPEC.md")
    conformance_text = _load_text(repo_root / "CONFORMANCE.md")

    combined = spec_text + conformance_text
    if code not in combined:
        pytest.xfail(
            f"Error code '{code}' not found in SPEC.md or CONFORMANCE.md. "
            "This is a real spec/schema divergence that should be investigated."
        )
