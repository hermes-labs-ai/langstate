"""Keep retracted research framing out of the tracked public truth surfaces."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACES = (
    *sorted(ROOT.glob("*.md*")),
    *sorted(ROOT.glob("*.txt")),
    *sorted((ROOT / "src" / "langstate").glob("*.py")),
    ROOT / "pyproject.toml",
    ROOT / "MANIFEST.in",
    ROOT / "te_check.py",
    ROOT / "bench" / "te_check.py",
)
RETIRED_PATTERNS = (
    re.compile(r"\bTE\b.{0,48}\b(?:zero|0(?:\.0+)?)\b", re.IGNORECASE | re.DOTALL),
    re.compile(
        r"transfer\s*-?\s*entropy.{0,96}\b(?:zero|0(?:\.0+)?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"Markov[- ]sufficien", re.IGNORECASE),
    re.compile(r"(?:0\.846|84\.6\s*%).{0,80}\bn\s*=\s*74\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bn\s*=\s*74\b.{0,80}(?:0\.846|84\.6\s*%)", re.IGNORECASE | re.DOTALL),
)


def test_retracted_claims_are_absent_from_public_truth_surfaces():
    for path in SURFACES:
        text = path.read_text()
        for pattern in RETIRED_PATTERNS:
            assert pattern.search(text) is None, (path, pattern.pattern)


def test_retracted_zero_claim_rephrasings_are_detected():
    variants = (
        "TE near 0",
        "TE was approximately zero",
        "transfer entropy around zero",
        "transfer\nentropy was nearly 0.0",
    )
    for text in variants:
        assert any(pattern.search(text) for pattern in RETIRED_PATTERNS)
