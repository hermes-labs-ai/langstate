"""Keep retracted research framing out of the tracked public truth surfaces."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "build", "dist", "__pycache__"}
SURFACES = tuple(
    sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not SKIP_PARTS.intersection(path.parts)
        and not any(part.endswith(".egg-info") for part in path.parts)
        and path != Path(__file__)
    )
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
    re.compile(r"preserv(?:e|es|ed|ing)\s+all\s+conversational\s+state", re.IGNORECASE),
    re.compile(r"\b(?:50\s*-\s*54|51\s*-\s*54)\s*%", re.IGNORECASE),
    re.compile(r"\b50\s*%\+\s*token", re.IGNORECASE),
)


def test_retracted_claims_are_absent_from_public_truth_surfaces():
    for path in SURFACES:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in RETIRED_PATTERNS:
            assert pattern.search(text) is None, (path, pattern.pattern)


def test_retracted_zero_claim_rephrasings_are_detected():
    variants = (
        "TE near 0",
        "TE was approximately zero",
        "transfer entropy around zero",
        "transfer\nentropy was nearly 0.0",
        "preserves all conversational state",
        "50-54% compression",
        "preserve state at 50%+ token reduction",
    )
    for text in variants:
        assert any(pattern.search(text) for pattern in RETIRED_PATTERNS)
