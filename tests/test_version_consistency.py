"""Version-of-record consistency (house policy: one source of truth, five mirrors).

Asserts the three in-repo version surfaces agree:
pyproject.toml == langstate.__version__ == newest CHANGELOG heading.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import tomllib
except ImportError:  # pragma: no cover (py<3.11)
    tomllib = None


def _pyproject_version() -> str:
    raw = (ROOT / "pyproject.toml").read_text()
    if tomllib is not None:
        return tomllib.loads(raw)["project"]["version"]
    match = re.search(r'^version = "([^"]+)"', raw, re.MULTILINE)
    assert match, "version line missing from pyproject.toml"
    return match.group(1)


def _source_version() -> str:
    source = (ROOT / "src" / "langstate" / "__init__.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise AssertionError("__version__ assignment missing from src/langstate/__init__.py")


def test_dunder_version_matches_pyproject():
    assert _source_version() == _pyproject_version()


def test_changelog_newest_heading_matches_pyproject():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    match = re.search(r"^## \[([^\]]+)\]", changelog, re.MULTILINE)
    assert match, "no versioned heading in CHANGELOG.md"
    assert match.group(1) == _pyproject_version()
