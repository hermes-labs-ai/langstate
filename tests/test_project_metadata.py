import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_homepage_points_to_canonical_product_page():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^Homepage = "([^"]+)"$', pyproject, re.MULTILINE)
    assert match
    assert match.group(1) == "https://hermes-labs.ai/langstate"
