"""Inspect the live-test marker without invoking an Ollama backend."""
import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize("value", [None, "", "0", "false", "1"])
def test_live_ollama_requires_explicit_one(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LANGSTATE_LIVE_OLLAMA", raising=False)
    else:
        monkeypatch.setenv("LANGSTATE_LIVE_OLLAMA", value)
    namespace = runpy.run_path(str(Path(__file__).with_name("test_compress.py")))
    marker = namespace["requires_ollama"]
    assert marker.args == (value != "1",)
