"""Version-of-record consistency (house policy: one source of truth, five mirrors).

Asserts the three in-repo version surfaces agree:
pyproject.toml == langstate.__version__ == newest CHANGELOG heading.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "src"))

import langstate  # noqa: E402

try:
    import tomllib
except ImportError:  # pragma: no cover (py<3.11)
    tomllib = None


def _pyproject_version() -> str:
    raw = (ROOT / "pyproject.toml").read_text()
    if tomllib is not None:
        return tomllib.loads(raw)["project"]["version"]
    match = re.search(r'^version = "([^"]+)"', raw, re.M)
    assert match, "version line missing from pyproject.toml"
    return match.group(1)


def test_dunder_version_matches_pyproject():
    assert langstate.__version__ == _pyproject_version()


def test_changelog_newest_heading_matches_pyproject():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    match = re.search(r"^## \[([^\]]+)\]", changelog, re.M)
    assert match, "no versioned heading in CHANGELOG.md"
    assert match.group(1) == _pyproject_version()
