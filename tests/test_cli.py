import json

from langstate.cli import main


def test_demo_is_local_and_deterministic(capsys):
    assert main(["demo"]) == 0
    first = capsys.readouterr().out
    assert main(["demo"]) == 0
    second = capsys.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload["receipt"]["ok"] is True
    assert payload["receipt"]["survived"] == ["Project: Atlas", "Budget: $4,000"]
