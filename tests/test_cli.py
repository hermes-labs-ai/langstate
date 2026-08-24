import json
from pathlib import Path

from langstate.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_demo_is_local_and_deterministic(capsys):
    assert main(["demo"]) == 0
    first = capsys.readouterr().out
    assert main(["demo"]) == 0
    second = capsys.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload["receipt"]["ok"] is True
    assert payload["receipt"]["survived"] == ["Project: Atlas", "Budget: $4,000"]


def test_public_quickstarts_lead_with_the_pinned_deterministic_demo():
    for relative_path in ["README.md", "SHOW-ME-FIRST.md", "llms.txt"]:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert content.count("langstate demo") == 1, relative_path
        demo_index = content.index("langstate demo")
        api_index = content.find("from langstate")
        assert api_index == -1 or demo_index < api_index, relative_path
        assert "langstate==0.2.2" in content, relative_path
