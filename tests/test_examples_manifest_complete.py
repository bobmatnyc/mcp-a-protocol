"""
Layer 2 coverage gate — Manifest completeness.

Why: Without this gate, a new example file added to examples/ could silently
     escape validation (no test ever exercises it).
What: Collects every *.json in examples/ (excluding README), checks each is
      present in MANIFEST; fails if any are missing.
Test: Add a fake examples/99-orphan.json and assert this test fails.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcpa_validation.mapping import MANIFEST


def test_manifest_covers_all_examples(repo_root: Path) -> None:
    """Assert every examples/*.json file is registered in the manifest.

    Why: Orphaned examples skip validation silently; this gate makes omissions
         a CI failure.
    What: Computes set(examples/*.json) - set(manifest example paths); fails
          if the difference is non-empty.
    Test: All current examples are in MANIFEST so this passes; add an unlisted
          file and it should fail with the filename in the error message.
    """
    examples_dir = repo_root / "examples"
    all_example_files = {
        f"examples/{p.name}"
        for p in examples_dir.glob("*.json")
        if p.name.lower() != "readme.md"
    }

    manifest_example_paths = {entry[0] for entry in MANIFEST if entry[0].startswith("examples/")}

    missing = all_example_files - manifest_example_paths
    if missing:
        missing_list = "\n  ".join(sorted(missing))
        pytest.fail(
            f"The following examples/*.json files are not in MANIFEST:\n  {missing_list}\n"
            "Add them to mcpa_validation/mapping.py with the correct schema."
        )
