"""Tests for langstate.compress — validates format, compression ratio, and state preservation."""

import os

import pytest

from langstate.compress import _build_compression_prompt, compress, _count_messages_tokens

# Live Ollama integration tests are opt-in so a default run never depends on
# what happens to be listening on localhost:11434. Set LANGSTATE_LIVE_OLLAMA=1
# (with qwen3:4b pulled) to run them; an unreachable backend then fails loudly.
requires_ollama = pytest.mark.skipif(
    not os.environ.get("LANGSTATE_LIVE_OLLAMA"),
    reason="live Ollama integration test; set LANGSTATE_LIVE_OLLAMA=1 to run",
)


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
    result = compress([])
    assert result == []
    assert validate_openai_format(result)


def test_one_turn():
    msgs = make_messages(1)
    result = compress(msgs)
    assert validate_openai_format(result)
    assert len(result) == len(msgs)


def test_five_turns():
    msgs = make_messages(5)
    result = compress(msgs)
    assert validate_openai_format(result)
    assert len(result) == len(msgs)


@pytest.mark.parametrize("preserve_recent", [0, 2])
def test_requested_recent_turns_and_remaining_history(preserve_recent):
    msgs = make_messages(6)
    prompts = []

    def summarize(prompt):
        prompts.append(prompt)
        return "Dana is building NoteFlow."

    result = compress(msgs, preserve_recent=preserve_recent, summarizer=summarize)
    history_end = len(msgs) - preserve_recent * 2
    history = msgs[1:history_end]
    recent = msgs[history_end:]
    assert result[0] == msgs[0]
    assert result[2:] == recent
    assert len(prompts) == 1
    for message in history:
        assert message["content"] in prompts[0]
    for message in recent:
        assert message["content"] not in prompts[0]
    assert f"compressed from {len(history)} earlier messages" in result[1]["content"]


def test_compression_prompt_does_not_promise_lossless_state():
    prompt = _build_compression_prompt("[USER]: important detail")
    assert "Do not claim that the summary is complete or lossless." in prompt


@pytest.mark.parametrize("preserve_recent", [-1, 1.5, "2", None, True, False])
def test_invalid_preserve_recent_is_rejected_before_summarizing(preserve_recent):
    msgs = make_messages(8)
    calls = []

    def summarize(prompt):
        calls.append(prompt)
        return "should-not-run"

    with pytest.raises(ValueError, match="preserve_recent"):
        compress(msgs, preserve_recent=preserve_recent, summarizer=summarize)
    assert calls == []


@pytest.mark.parametrize("summary", ["", "   \n\t"])
def test_blank_summary_does_not_silently_drop_history(summary):
    msgs = make_messages(8)
    with pytest.raises(RuntimeError, match="empty output"):
        compress(msgs, summarizer=lambda _prompt: summary)


def test_non_string_summary_is_rejected():
    msgs = make_messages(8)
    with pytest.raises(TypeError, match="summarizer must return str"):
        compress(msgs, summarizer=lambda _prompt: None)


@requires_ollama
def test_twenty_turns():
    msgs = make_messages(20)
    result = compress(msgs)
    assert validate_openai_format(result)
    input_tokens = _count_messages_tokens(msgs)
    output_tokens = _count_messages_tokens(result)
    ratio = 1 - (output_tokens / input_tokens) if input_tokens > 0 else 0
    assert ratio > 0.25
    assert len(result) < len(msgs)


@requires_ollama
def test_twenty_five_turns():
    msgs = make_messages(25)
    result = compress(msgs)
    assert validate_openai_format(result)
    input_tokens = _count_messages_tokens(msgs)
    output_tokens = _count_messages_tokens(result)
    ratio = 1 - (output_tokens / input_tokens) if input_tokens > 0 else 0
    assert ratio > 0.25


@requires_ollama
def test_state_preservation():
    msgs = make_messages(20)
    compressed = compress(msgs)
    scaffold_content = ""
    for m in compressed:
        if m["role"] == "system" and "SCAFFOLD STATE" in m.get("content", ""):
            scaffold_content = m["content"]
            break
    assert scaffold_content, "No scaffold state message found in compressed output"
    checks = {
        "project name (Dana/NoteFlow)": any(w in scaffold_content.lower() for w in ["dana", "noteflow"]),
        "grouping accuracy": any(w in scaffold_content.lower() for w in ["78%", "78", "accuracy"]),
    }
    # At least the project name must appear in scaffold
    assert checks["project name (Dana/NoteFlow)"], f"Project name not in scaffold: {scaffold_content[:300]}"
