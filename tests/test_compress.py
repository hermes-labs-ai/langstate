"""Tests for langstate.compress — validates format, compression ratio, and state preservation."""

import urllib.error
import urllib.request

import pytest

from langstate.compress import compress, _count_messages_tokens


def _ollama_reachable() -> bool:
    """Check if Ollama is running at localhost:11434. CI runners don't have it."""
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_reachable(),
    reason="requires local Ollama at :11434 (integration test)",
)


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
        "company name (Roli/Hermes)": any(w in scaffold_content.lower() for w in ["roli", "hermes"]),
        "compression ratio": any(w in scaffold_content.lower() for w in ["2.5x", "2.5", "compression"]),
    }
    # At least company name must appear in scaffold
    assert checks["company name (Roli/Hermes)"], f"Company name not in scaffold: {scaffold_content[:300]}"
