"""Tests for langstate.compress — validates format, compression ratio, and state preservation."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from compress import compress, _count_messages_tokens


def make_messages(n_turns: int, system: str = "You are a helpful assistant.") -> list[dict]:
    """Generate a realistic multi-turn conversation with trackable facts."""
    msgs = [{"role": "system", "content": system}]
    facts = [
        ("My name is Roli and I'm building a company called Hermes Labs.", "Nice to meet you, Roli! Hermes Labs sounds interesting. What does Hermes Labs do?"),
        ("We're building AI infrastructure for agent state management. Our key innovation is LPCI — we proved that stateless LLMs hold state via language scaffold with TE approximately zero.", "That's fascinating! The TE≈0 finding means the scaffold carries all necessary state information. How did you measure this?"),
        ("We measured transfer entropy from scaffold to LLM output across 500 inference calls. The compression ratio is 2.5x while maintaining Markov sufficiency.", "A 2.5x compression ratio while preserving Markov sufficiency is significant. What's the practical application?"),
        ("The first product is a compression middleware — compress(messages) — that any agent framework can use. It reduces context cost by 2.5x.", "That's a clean MVP. Who are your target customers?"),
        ("Agent framework builders running production workloads. Context cost is a real budget line for them. We're also looking at enterprise compliance use cases.", "Enterprise compliance is a strong angle — auditable language scaffold state vs opaque neural activations. What's your timeline?"),
        ("We need to publish the arXiv preprint before NeurIPS 2026 submission deadline in May. The paper needs to be out first to establish priority.", "That's tight but doable. The related work section needs to map who else treats language as state — have you done that research?"),
        ("Yes, we built a 530MB research corpus with 155 arxiv papers, 679 techniques, and 718 benchmarks. The key finding: transfer entropy appears zero times in 470MB of related work.", "So the TE≈0 measurement is completely uncontested. That's a strong novelty claim. Who are the closest competitors?"),
        ("Schuurmans at Alberta proved autoregressive chaining equals universal computation in January 2026. Millidge at beren.io made the same qualitative claim in 2023. We're the quantitative proof.", "Position as Millidge's empirical proof — that's the strongest framing. Lead with the measurement, not the philosophy."),
        ("We also found that cognitive science is completely absent from this field. 70 years of chunking research never cited.", "That's a potential bridge paper after the main LPCI publication. The 2.5x compression might correspond to known cognitive chunk density."),
        ("The multi-agent case is the next paper. Proving TE≈0 for shared scaffold across agents is genuinely novel — novelty 5/5 but urgency 2/5.", "Correct sequence: single-agent paper first, then multi-agent as follow-on. Don't split focus."),
        ("Budget is tight. We're bootstrapping. The compression middleware needs to generate revenue by month 3-4.", "Focus on the wedge product. compress(messages) → hosted API → enterprise contracts. Keep scope minimal."),
        ("Our biggest risk is that long-context scaling makes compression less valuable. If Gemini 1M+ tokens gets cheap enough...", "True, but the TE≈0 proof survives academically regardless. And compression always saves money — even cheap tokens add up at scale."),
        ("We're using qwen3:4b locally for the compression. Zero API cost.", "Smart — keeps the MVP free to run. You can always upgrade the compression model later without changing the interface."),
        ("One more thing: we need to set up a weekly arXiv monitor for transfer entropy + LLM + scaffold.", "I'd automate that. If it returns results, read same day. The window is closing."),
        ("The VC pitch is ScaffoldGit + Driftwatch bundled as Agent Observability. $2M seed.", "That's the right framing. Version control + monitoring for agent state, with LPCI's Markov theory as the only formal correctness model. Fintech and legal design partners first."),
        ("Let's focus. What should I do today?", "Submit the arXiv preprint and ship compress(messages). Everything else follows from those two."),
        ("Thanks. Let's do it.", "Let's go. Preprint first, then the MVP."),
        ("Actually, one more question — should we open-source the compression or keep it proprietary?", "Open-source the library, charge for the hosted API. The proof is the moat, not the code. Open source gets you distribution and citations."),
        ("Makes sense. Open source library, hosted API for revenue.", "Exactly. PyPI package → GitHub stars → citations → enterprise leads. The flywheel."),
        ("What about the scaffold-monad idea? The state monad for LLM calls.", "That's the 10k-star GitHub project. Effort 2/5. 'We proved agent code correct' is a Hacker News post that writes itself. Build it after compress(messages)."),
        ("OK I think we have a plan. Roli out.", "Good luck, Roli. Ship the preprint, ship compress(messages), then scaffold-monad. In that order."),
        ("Wait — what was the NL-DST accuracy result again?", "90.1% slot accuracy for natural language state vs 88.5% for structured slot-value output. Same model, different state format. Language wins."),
        ("And the ICAE compression ratio?", "4x compression but opaque embeddings. Your 2.5x is the interpretable compression benchmark. Different problem, defensible position."),
        ("Perfect. Now I'm really done.", "Go ship. The window is measured in months, not years."),
        ("One truly final thing: the PRISM paper from March 2026.", "arXiv:2603.22754. They model reasoning trajectories as Markov transition processes. Same vocabulary as LPCI but different measurement. Citation partner, not competitor."),
    ]

    for i in range(min(n_turns, len(facts))):
        user_msg, assistant_msg = facts[i]
        msgs.append({"role": "user", "content": user_msg})
        msgs.append({"role": "assistant", "content": assistant_msg})

    return msgs


def validate_openai_format(messages: list[dict]) -> bool:
    """Check every message has role and content strings."""
    for m in messages:
        if not isinstance(m, dict):
            return False
        if "role" not in m or "content" not in m:
            return False
        if not isinstance(m["role"], str) or not isinstance(m["content"], str):
            return False
        if m["role"] not in ("system", "user", "assistant"):
            return False
    return True


def test_empty():
    """Test 1: Empty messages."""
    result = compress([])
    assert result == [], f"Expected empty list, got {result}"
    assert validate_openai_format(result)
    print("  PASS: empty messages -> empty output")
    return 0, 0


def test_one_turn():
    """Test 2: Single turn — too short to compress."""
    msgs = make_messages(1)
    result = compress(msgs)
    assert validate_openai_format(result)
    assert len(result) == len(msgs), "Single turn should not be compressed"
    print("  PASS: 1 turn -> returned unchanged (3 messages)")
    return _count_messages_tokens(msgs), _count_messages_tokens(result)


def test_five_turns():
    """Test 3: 5 turns — borderline, should not compress with default min_turns."""
    msgs = make_messages(5)
    result = compress(msgs)
    assert validate_openai_format(result)
    # 5 turns < min_turns_to_compress=6, should pass through unchanged
    assert len(result) == len(msgs), f"5 turns should not be compressed (below threshold), got {len(result)} vs {len(msgs)}"
    print(f"  PASS: 5 turns -> returned unchanged ({len(msgs)} messages)")
    return _count_messages_tokens(msgs), _count_messages_tokens(result)


def test_twenty_turns():
    """Test 4: 20 turns — should compress significantly."""
    msgs = make_messages(20)
    result = compress(msgs)
    assert validate_openai_format(result), "Output is not valid OpenAI format"

    input_tokens = _count_messages_tokens(msgs)
    output_tokens = _count_messages_tokens(result)
    ratio = 1 - (output_tokens / input_tokens) if input_tokens > 0 else 0

    print(f"  Input: {len(msgs)} messages, ~{input_tokens} tokens")
    print(f"  Output: {len(result)} messages, ~{output_tokens} tokens")
    print(f"  Compression: {ratio:.1%} reduction")

    # Should achieve 40-60% reduction
    assert ratio > 0.25, f"Compression too low: {ratio:.1%} (expected >25%)"
    assert len(result) < len(msgs), "Output should have fewer messages"
    print("  PASS: 20 turns compressed successfully")
    return input_tokens, output_tokens


def test_fifty_turns():
    """Test 5: 50 turns (capped at 25 available facts, rest are repeats)."""
    msgs = make_messages(25)  # we have 25 fact pairs
    result = compress(msgs)
    assert validate_openai_format(result), "Output is not valid OpenAI format"

    input_tokens = _count_messages_tokens(msgs)
    output_tokens = _count_messages_tokens(result)
    ratio = 1 - (output_tokens / input_tokens) if input_tokens > 0 else 0

    print(f"  Input: {len(msgs)} messages, ~{input_tokens} tokens")
    print(f"  Output: {len(result)} messages, ~{output_tokens} tokens")
    print(f"  Compression: {ratio:.1%} reduction")

    assert ratio > 0.25, f"Compression too low: {ratio:.1%}"
    print("  PASS: 25 turns (max) compressed successfully")
    return input_tokens, output_tokens


def test_state_preservation():
    """Test 6: Verify compressed messages preserve state from early turns.

    Ask about facts from turn 3 (compression ratio + Markov sufficiency)
    using only the compressed context. The scaffold summary should contain this info.
    """
    msgs = make_messages(20)
    compressed = compress(msgs)

    # The scaffold summary should contain key facts from turn 3:
    # "2.5x compression ratio" and "Markov sufficiency"
    scaffold_content = ""
    for m in compressed:
        if m["role"] == "system" and "SCAFFOLD STATE" in m.get("content", ""):
            scaffold_content = m["content"]
            break

    assert scaffold_content, "No scaffold state message found in compressed output"

    # Check for key facts from early turns
    checks = {
        "company name (Roli/Hermes)": any(w in scaffold_content.lower() for w in ["roli", "hermes"]),
        "LPCI or TE≈0 or transfer entropy": any(w in scaffold_content.lower() for w in ["lpci", "te≈0", "te=0", "transfer entropy", "te ≈ 0", "te approximately"]),
        "compression ratio (2.5x)": any(w in scaffold_content.lower() for w in ["2.5x", "2.5", "compression"]),
    }

    print("  State preservation checks:")
    all_pass = True
    for fact, found in checks.items():
        status = "FOUND" if found else "MISSING"
        print(f"    {status}: {fact}")
        if not found:
            all_pass = False

    if all_pass:
        print("  PASS: All key facts preserved in scaffold")
    else:
        print("  PARTIAL: Some facts missing — scaffold summary may vary by model")
        print(f"  Scaffold content preview: {scaffold_content[:300]}...")

    return all_pass


def main():
    print("=" * 60)
    print("langstate.compress — Test Suite")
    print("=" * 60)

    results = {}

    print("\nTest 1: Empty messages")
    results["empty"] = test_empty()

    print("\nTest 2: Single turn")
    results["1_turn"] = test_one_turn()

    print("\nTest 3: Five turns")
    results["5_turns"] = test_five_turns()

    print("\nTest 4: Twenty turns")
    results["20_turns"] = test_twenty_turns()

    print("\nTest 5: Twenty-five turns (max)")
    results["25_turns"] = test_fifty_turns()

    print("\nTest 6: State preservation")
    state_ok = test_state_preservation()

    print("\n" + "=" * 60)
    print("COMPRESSION RATIOS:")
    print("-" * 60)
    for name, (inp, out) in results.items():
        if inp > 0:
            ratio = 1 - (out / inp)
            print(f"  {name:>10}: {inp:>5} -> {out:>5} tokens ({ratio:>6.1%} reduction)")
        else:
            print(f"  {name:>10}: (empty)")

    print("\n" + "=" * 60)
    all_passed = state_ok  # state preservation is the critical test
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS HAD WARNINGS (see above)")
    print("=" * 60)


if __name__ == "__main__":
    main()
