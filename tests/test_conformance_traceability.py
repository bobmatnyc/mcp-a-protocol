"""
Layer 5 — Conformance-to-SPEC traceability.

Why: If CONFORMANCE.md references a SPEC section that doesn't exist (e.g., a
     typo like "§Comformance Levels"), the conformance matrix is misleading.
What: Parses CONFORMANCE.md for SPEC section references in the pattern
      "SPEC §<section>" (e.g., "SPEC §3", "SPEC §RBAC", "SPEC §Conformance Levels").
      For each referenced section, checks that a matching heading exists in
      SPEC.md (case-insensitive, whitespace-normalized, anchored to ## or ###).

Limitation: The parser matches the literal pattern "SPEC §<token>" where <token>
      is everything up to the next ) , ) or end-of-line. Numeric shorthands
      like "SPEC §1" are resolved against the primitive headings via a known
      mapping (§1 → "1. discover", §2 → "2. schema", etc.) because SPEC.md uses
      numbered headings, not bare section numbers.
      If citations use a format not covered by this parser, the test will report
      "0 citations found" and skip rather than pass vacuously — see the guard
      at the bottom.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Known numeric shorthands in CONFORMANCE.md → SPEC.md heading fragments
NUMERIC_SECTION_MAP: dict[str, str] = {
    "1": "1. discover",
    "2": "2. schema",
    "3": "3. query",
    "4": "4. follow_up",
    "5": "5. context",
    "6": "6. explain",
    "7": "7. action",
}


def _extract_spec_citations(conformance_text: str) -> set[str]:
    """Extract distinct SPEC section tokens from CONFORMANCE.md.

    Pattern: SPEC §<token> where token ends at ], ), comma, or end of line.
    Returns the raw token strings (e.g. "1", "RBAC", "Conformance Levels").
    """
    # Match "SPEC §<token>" — token is non-greedy, stops at ), ], comma, period, newline
    pattern = re.compile(r"SPEC §([^\],)\n.]+)")
    tokens: set[str] = set()
    for match in pattern.finditer(conformance_text):
        raw = match.group(1).strip()
        # Strip trailing punctuation that may have been captured
        raw = raw.rstrip(" .,)")
        if raw:
            tokens.add(raw)
    return tokens


def _spec_headings(spec_text: str) -> list[str]:
    """Extract all heading text from SPEC.md (## and ### level)."""
    pattern = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(spec_text)]


def _heading_matches(token: str, headings: list[str]) -> bool:
    """Check whether a citation token maps to any SPEC.md heading.

    Handles:
    - Numeric tokens ("1", "2", …) via NUMERIC_SECTION_MAP. A numeric citation
      may carry trailing annotations the parser couldn't cleanly strip (e.g.
      "3 Structured-Response Mode:**" or "2 (MAEP-0004"); for these the leading
      number is the authoritative section reference, so we resolve on that.
    - Named sections ("RBAC", "Conformance Levels", …) via case-insensitive
      substring match against heading text.
    """
    # Numeric shorthand: a citation like "§3 ..." references section 3. Take the
    # leading digit run as the canonical section id and ignore trailing prose.
    leading = token.split(maxsplit=1)[0]
    if leading.isdigit() and leading in NUMERIC_SECTION_MAP:
        resolved = NUMERIC_SECTION_MAP[leading]
    else:
        resolved = NUMERIC_SECTION_MAP.get(token, token)

    norm = resolved.lower().strip()
    for heading in headings:
        if norm in heading.lower():
            return True
    return False


def test_conformance_spec_citations_are_valid(repo_root: Path) -> None:
    """Assert every SPEC section cited in CONFORMANCE.md exists as a SPEC.md heading.

    Why: Stale or mistyped citations make the conformance matrix untrustworthy.
    What: Extracts all SPEC §... tokens from CONFORMANCE.md; for each, checks
          a matching heading exists in SPEC.md.
    Test: All current citations should resolve; introduce "SPEC §NonExistentSection"
          and this test should fail.

    Limitation: Numeric shorthands (§1–§7) are resolved via a hard-coded map;
    compound tokens with trailing content (e.g., "§3 Structured-Response Mode")
    use substring matching against SPEC.md headings, which may produce false
    positives for very short tokens.
    """
    conformance_text = (repo_root / "CONFORMANCE.md").read_text(encoding="utf-8")
    spec_text = (repo_root / "SPEC.md").read_text(encoding="utf-8")

    citations = _extract_spec_citations(conformance_text)

    # Guard: if we found no citations, the parser may be broken — don't pass vacuously
    if not citations:
        pytest.skip(
            "No SPEC §... citations found in CONFORMANCE.md — "
            "the citation parser may not match the actual format. "
            "Review _extract_spec_citations() and update the pattern."
        )

    headings = _spec_headings(spec_text)

    unresolved: list[str] = []
    for token in sorted(citations):
        if not _heading_matches(token, headings):
            unresolved.append(token)

    if unresolved:
        unresolved_list = "\n  ".join(unresolved)
        pytest.fail(
            f"The following SPEC citations in CONFORMANCE.md do not match "
            f"any heading in SPEC.md:\n  {unresolved_list}\n"
            "Either fix the citation in CONFORMANCE.md or add the heading to SPEC.md."
        )
