"""
Shared pytest fixtures for the MCP-A validation suite.

Why: Centralizes repo_root, schemas_dir, registry, and the validator factory
     so every test module can share a single session-scoped registry instance.
What: Provides repo_root (Path), schemas_dir (Path), registry (Registry),
      and validator_for(schema_id) -> Draft202012Validator.
Test: Import conftest fixtures in any test; assert registry resolves known IDs.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from mcpa_validation.registry import build_registry


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Why: Single source of truth for the repo root path across all tests.
    What: Returns the parent-parent directory of this conftest file (tests/../).
    Test: Assert repo_root / 'SPEC.md' exists.
    """
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def schemas_dir(repo_root: Path) -> Path:
    """Why: Convenience alias so tests don't construct paths manually.
    What: Returns repo_root / 'schemas'.
    Test: Assert schemas_dir.is_dir().
    """
    return repo_root / "schemas"


@pytest.fixture(scope="session")
def registry(schemas_dir: Path) -> Registry:
    """Why: Session-scoped to build the $id registry once and share it.
    What: Calls build_registry(schemas_dir) and returns the result.
    Test: Assert registry resolves https://mcp-a.dev/schemas/error.json.
    """
    return build_registry(schemas_dir)


@pytest.fixture(scope="session")
def validator_for(registry: Registry):
    """Why: Factory fixture so each test can get a validator for any schema ID.
    What: Returns a callable that accepts a schema dict and returns a
          Draft202012Validator configured with the shared registry and
          FormatChecker (for date-time/uri format validation).
    Test: Call validator_for(schema) and assert .validate({}) raises on an
          invalid instance.
    """
    def _factory(schema: dict) -> Draft202012Validator:
        return Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
    return _factory
