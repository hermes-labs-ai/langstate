"""
Tests for langstate.adapters — validates the adapter protocol, registry,
and that compress() honours a user-supplied summarizer without touching
the network.

These tests do NOT hit any real backend. They inject a fake summarizer
callable to prove the wiring works deterministically. The live network
benches live in bench_adapters.py.
"""

import os

from langstate.adapters import AdapterUnavailable, REGISTRY, build, probe
from langstate.compress import _count_messages_tokens, compress


def _corpus(n_turns: int = 10) -> list[dict]:
    msgs = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(n_turns):
        msgs.append({"role": "user",      "content": f"user turn {i}: fact-{i} matters."})
        msgs.append({"role": "assistant", "content": f"assistant turn {i}: got it."})
    return msgs


def test_registry_has_three_production_adapters():
    assert set(REGISTRY) == {"local", "openai", "anthropic"}
    labels = {name: REGISTRY[name][0] for name in REGISTRY}
    assert "qwen3:4b" in labels["local"]
    assert "gpt-4o-mini" in labels["openai"]
    assert "claude-haiku-4-5" in labels["anthropic"]


def test_build_openai_without_key_raises_adapter_unavailable():
    saved = os.environ.pop("OPENAI_API_KEY", None)
    try:
        try:
            build("openai")
        except AdapterUnavailable as e:
            assert "OPENAI_API_KEY" in str(e)
        else:
            raise AssertionError("expected AdapterUnavailable when key absent")
    finally:
        if saved is not None:
            os.environ["OPENAI_API_KEY"] = saved


def test_build_anthropic_without_key_raises_adapter_unavailable():
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        try:
            build("anthropic")
        except AdapterUnavailable as e:
            assert "ANTHROPIC_API_KEY" in str(e)
        else:
            raise AssertionError("expected AdapterUnavailable when key absent")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_compress_accepts_custom_summarizer_without_network():
    calls = []

    def fake(prompt: str) -> str:
        calls.append(prompt)
        return "- fact-0 matters\n- fact-1 matters\n- remaining facts preserved"

    msgs = _corpus(10)
    compressed = compress(msgs, summarizer=fake)
    assert len(calls) == 1
    scaffold = next(
        (m for m in compressed if m["role"] == "system" and "SCAFFOLD STATE" in m.get("content", "")),
        None,
    )
    assert scaffold is not None
    assert "fact-0" in scaffold["content"]


def test_compress_below_threshold_skips_summarizer():
    calls = []

    def fake(prompt: str) -> str:
        calls.append(prompt)
        return "should-not-run"

    msgs = _corpus(3)
    out = compress(msgs, summarizer=fake)
    assert calls == []
    assert out == msgs


def test_compress_reduces_tokens_with_custom_summarizer():
    def fake(prompt: str) -> str:
        return "scaffold: all facts preserved in this terse state summary."

    msgs = _corpus(15)
    before = _count_messages_tokens(msgs)
    out = compress(msgs, summarizer=fake)
    after = _count_messages_tokens(out)
    assert after < before


def test_probe_of_unavailable_returns_structured_failure():
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        r = probe("anthropic")
        assert r["name"] == "anthropic"
        assert r["available"] is False
        assert "ANTHROPIC_API_KEY" in r["reason"]
        assert r["latency_ms"] is None
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
