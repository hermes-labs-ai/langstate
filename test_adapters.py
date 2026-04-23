"""
Tests for langstate.adapters — validates the adapter protocol, registry,
and that compress() honours a user-supplied summarizer without touching
the network.

These tests do NOT hit any real backend. They inject a fake summarizer
callable to prove the wiring works deterministically. The live network
benches live in bench_adapters.py.
"""

import os
import sys

HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from adapters import AdapterUnavailable, REGISTRY, build, probe  # noqa: E402
from compress import _count_messages_tokens, compress  # noqa: E402


def _corpus(n_turns: int = 10) -> list[dict]:
    msgs = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(n_turns):
        msgs.append({"role": "user",      "content": f"user turn {i}: fact-{i} matters."})
        msgs.append({"role": "assistant", "content": f"assistant turn {i}: got it."})
    return msgs


def test_registry_has_three_production_adapters():
    """Pins the three-adapter production surface from the Hermes spec."""
    assert set(REGISTRY) == {"local", "openai", "anthropic"}, (
        "registry must expose local, openai, and anthropic adapters"
    )
    # Labels must name the production model defaults.
    labels = {name: REGISTRY[name][0] for name in REGISTRY}
    assert "qwen3:14b" in labels["local"],       labels
    assert "gpt-4o-mini" in labels["openai"],    labels
    assert "claude-opus-4-7" in labels["anthropic"], labels


def test_build_openai_without_key_raises_adapter_unavailable():
    """Missing key must produce AdapterUnavailable, not a generic Exception."""
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
    """compress() must use the injected summarizer callable verbatim."""
    calls = []

    def fake(prompt: str) -> str:
        calls.append(prompt)
        # Return a terse scaffold that references the seed facts.
        return "- fact-0 matters\n- fact-1 matters\n- remaining facts preserved"

    msgs = _corpus(10)
    compressed = compress(msgs, summarizer=fake)

    # The summarizer must have been called exactly once.
    assert len(calls) == 1, f"expected one summarizer call, got {len(calls)}"
    # The compressed output must contain a scaffold system message.
    scaffold = next(
        (m for m in compressed if m["role"] == "system" and "SCAFFOLD STATE" in m.get("content", "")),
        None,
    )
    assert scaffold is not None, "no SCAFFOLD STATE message in compressed output"
    # Network was never touched: no adapter built, no Ollama call.
    assert "fact-0" in scaffold["content"]


def test_compress_below_threshold_skips_summarizer():
    """Short conversations must not invoke the summarizer at all."""
    calls = []

    def fake(prompt: str) -> str:
        calls.append(prompt)
        return "should-not-run"

    msgs = _corpus(3)  # 3 turns < default min_turns_to_compress=6
    out = compress(msgs, summarizer=fake)
    assert calls == [], "summarizer must not run below min_turns_to_compress"
    assert out == msgs, "below-threshold input should pass through unchanged"


def test_compress_reduces_tokens_with_custom_summarizer():
    """End-to-end: fake summarizer + long corpus must cut tokens."""
    def fake(prompt: str) -> str:
        return "scaffold: all facts preserved in this terse state summary."

    msgs = _corpus(15)
    before = _count_messages_tokens(msgs)
    out = compress(msgs, summarizer=fake)
    after = _count_messages_tokens(out)
    assert after < before, f"tokens did not shrink: {before} -> {after}"


def test_probe_of_unavailable_returns_structured_failure():
    """probe() on an unavailable adapter must return a machine-readable row."""
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


def main() -> int:
    tests = [
        test_registry_has_three_production_adapters,
        test_build_openai_without_key_raises_adapter_unavailable,
        test_build_anthropic_without_key_raises_adapter_unavailable,
        test_compress_accepts_custom_summarizer_without_network,
        test_compress_below_threshold_skips_summarizer,
        test_compress_reduces_tokens_with_custom_summarizer,
        test_probe_of_unavailable_returns_structured_failure,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {t.__name__}: {type(e).__name__}: {e}")
            failures += 1
        else:
            print(f"PASS  {t.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
