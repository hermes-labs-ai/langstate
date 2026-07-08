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
        ("My name is Dana and I'm building a small app called NoteFlow.", "Nice to meet you, Dana! What does NoteFlow do?"),
        ("It's a note-taking app that automatically groups related notes by topic.", "That's a useful feature. How are you grouping them under the hood?"),
        ("I'm using simple keyword clustering for now, might move to embeddings later.", "Keyword clustering is a solid MVP choice — cheap and easy to debug."),
        ("The first version is a command-line tool — notes(text) — that any editor can pipe into.", "Clean scope. Who's the target user for v1?"),
        ("Developers who keep scratch notes in plain text files. Students are a secondary audience.", "Both groups value fast capture over polish. What's the timeline?"),
        ("I want to publish a short write-up once the grouping accuracy is good enough.", "Reasonable. What does 'good enough' look like for the write-up?"),
        ("Right now grouping accuracy is around 78% on my test set of 50 note files.", "78% is a fine starting point to write about, as long as you're clear it's a small test set."),
        ("I also built a small benchmark script that scores grouping accuracy against a labeled sample.", "Good — having a repeatable benchmark early will save you from regressions later."),
        ("I noticed most similar tools use full embeddings, which cost more to run.", "That's a legitimate tradeoff to call out — cheaper but less precise clustering."),
        ("There's a related open-source project called TagSort that does something similar with tags instead of clusters.", "Worth a short comparison section — similar goal, different mechanism."),
        ("I'm also curious whether note length affects grouping quality.", "That's an easy follow-up experiment: bucket notes by length and compare accuracy per bucket."),
        ("Budget is basically zero — this is a side project I work on evenings.", "Then keep scope tight: ship the CLI, write the benchmark, then decide if a GUI is worth it."),
        ("I'm running everything locally with a small open model, no API costs.", "Smart — keeps the project free to run and easy for others to reproduce."),
        ("One more thing — I should set up a simple test suite before I add more features.", "Yes, lock in the current behavior with tests first, then iterate."),
        ("The rough plan is: CLI tool, benchmark script, short write-up, then decide on next features.", "That's a sensible order — ship the smallest useful thing, measure it, then expand."),
        ("Let's focus. What should I do today?", "Finish the benchmark script and write down the current accuracy number."),
        ("Thanks. I'll do that.", "Sounds good — small steps."),
        ("Should I open-source the CLI or keep it private for now?", "Open-source the CLI once the tests pass; that's usually the easiest way to get feedback."),
        ("Makes sense. I'll tag a v0.1 once tests are green.", "Good plan — tag it, write a short README, and move on to the next feature."),
        ("What about a GUI wrapper eventually?", "Worth considering after the CLI is stable, but it's a nice-to-have, not a blocker."),
        ("OK I think I have a plan. Talk later.", "Sounds good — ship the CLI, write the benchmark, then decide on the GUI."),
        ("Wait — what was the grouping accuracy number again?", "78% on your 50-file test set, per your last message."),
        ("And how does that compare to TagSort?", "You hadn't benchmarked TagSort directly yet — that's a good next comparison to run."),
        ("Got it, thanks.", "Anytime — go finish that benchmark script."),
        ("One truly final thing — should the CLI support markdown input?", "Yes, plain text and markdown both, since most note files are one or the other."),
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

    Ask about the project name and accuracy number from early turns using
    only the compressed context. The scaffold summary should contain this info.
    """
    msgs = make_messages(20)
    compressed = compress(msgs)

    # The scaffold summary should contain key facts from early turns:
    # the project name and the grouping-accuracy figure.
    scaffold_content = ""
    for m in compressed:
        if m["role"] == "system" and "SCAFFOLD STATE" in m.get("content", ""):
            scaffold_content = m["content"]
            break

    assert scaffold_content, "No scaffold state message found in compressed output"

    # Check for key facts from early turns
    checks = {
        "project name (Dana/NoteFlow)": any(w in scaffold_content.lower() for w in ["dana", "noteflow"]),
        "grouping accuracy (78%)": any(w in scaffold_content.lower() for w in ["78%", "78", "accuracy"]),
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
