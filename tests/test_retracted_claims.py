"""Keep retracted research framing out of the tracked public truth surfaces."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACES = (
    ROOT / "README.md",
    ROOT / "llms.txt",
    ROOT / "AGENTS.md",
    ROOT / "TODO.md",
    ROOT / "SCRUB-0.1.1-READY.md",
    ROOT / "te_check.py",
    ROOT / "bench" / "te_check.py",
)
RETIRED_PATTERNS = (
    re.compile(r"\bTE\s*(?:approximately|[≈~=])\s*0", re.IGNORECASE),
    re.compile(r"transfer[- ]entropy.{0,80}(?:approximately|[≈~=]|near(?:ly)?)\s*0", re.IGNORECASE | re.DOTALL),
    re.compile(r"Markov[- ]sufficien", re.IGNORECASE),
    re.compile(r"(?:0\.846|84\.6\s*%).{0,80}\bn\s*=\s*74\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bn\s*=\s*74\b.{0,80}(?:0\.846|84\.6\s*%)", re.IGNORECASE | re.DOTALL),
)


def test_retracted_claims_are_absent_from_public_truth_surfaces():
    for path in SURFACES:
        text = path.read_text()
        for pattern in RETIRED_PATTERNS:
            assert pattern.search(text) is None, (path, pattern.pattern)
