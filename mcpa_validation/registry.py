"""
Why: Centralizes offline $id-based cross-file $ref resolution so all validators
     share one registry keyed by each schema's $id URI.
What: Loads all *.json files from schemas_dir, builds a referencing.Registry
      keyed by each file's "$id"; skips files without "$id".
Test: Call build_registry(schemas_dir) and assert the registry resolves
      "https://mcp-a.dev/schemas/common.defs.json".
"""
from __future__ import annotations

import json
from pathlib import Path

from referencing import Registry, Resource


def load_json(path: Path) -> dict:
    """Load and return a JSON file as a dict.

    Why: Shared helper to avoid duplicating open/json.load calls.
    What: Opens path, parses JSON, returns dict.
    Test: Pass a valid JSON path, assert result is a dict.
    """
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def build_registry(schemas_dir: Path) -> Registry:
    """Build a referencing.Registry from all top-level schema files.

    Why: MCP-A schemas use absolute $id-based cross-file $refs
         (https://mcp-a.dev/schemas/...) which are NOT live URLs. A Registry
         keyed by $id enables offline resolution.
    What: Iterates *.json in schemas_dir (not subdirs), collects files that have
          a "$id" key, and registers each as a Resource. Returns the Registry.
    Test: Assert registry resolves https://mcp-a.dev/schemas/common.defs.json
          and https://mcp-a.dev/schemas/error.json without network access.
    """
    resources: list[tuple[str, Resource]] = []
    for schema_path in sorted(schemas_dir.glob("*.json")):
        schema = load_json(schema_path)
        schema_id = schema.get("$id")
        if schema_id:
            resources.append((schema_id, Resource.from_contents(schema)))
    registry: Registry = Registry().with_resources(resources)
    return registry
