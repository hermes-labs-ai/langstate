"""
langstate.compress — Scaffold-aware context compression for OpenAI-format messages.

Compresses conversation history into a state-preserving scaffold summary,
keeping the system prompt and recent turns verbatim. Uses a local Ollama
model (qwen3:4b) for zero-cost summarization.

Usage:
    from langstate.compress import compress
    compressed = compress(messages)
    response = client.chat.completions.create(messages=compressed, model="gpt-4o")
"""

import json
import urllib.request
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3:4b"
PRESERVE_RECENT = 4  # keep last N user/assistant turns verbatim


def _count_tokens_approx(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return len(text) // 4


def _count_messages_tokens(messages: list[dict]) -> int:
    """Approximate total tokens across all messages."""
    return sum(_count_tokens_approx(m.get("content", "")) for m in messages)


def _summarize_via_ollama(
    text: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
) -> str:
    """Call local Ollama to produce a scaffold-aware summary."""
    summary_prompt = (
        "You are a scaffold state compressor. Your job is to compress a conversation "
        "history into a concise state summary that preserves ALL of the following:\n"
        "- Facts established (names, numbers, decisions, entities)\n"
        "- Decisions made and their reasoning\n"
        "- Current task state (what's done, what's pending, what's blocked)\n"
        "- User preferences and constraints expressed\n"
        "- Any commitments or agreements\n\n"
        "Do NOT preserve:\n"
        "- Greetings, pleasantries, filler\n"
        "- Redundant re-statements of the same fact\n"
        "- Verbose explanations when a short statement captures the same info\n\n"
        "Output a compressed state summary in natural language. Use bullet points for "
        "distinct facts. Be terse but complete. Preserve every fact and decision.\n\n"
        "CONVERSATION TO COMPRESS:\n"
        f"{text}"
    )

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Respond directly. Do not think or reason. Just output the summary."},
            {"role": "user", "content": summary_prompt},
        ],
        "stream": False,
        "options": {"num_predict": 8000, "temperature": 0.2},
    }).encode()

    req = urllib.request.Request(
        ollama_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())

    content = result.get("message", {}).get("content", "")
    if not content.strip():
        raise RuntimeError("Ollama returned empty content. Model may need more num_predict tokens.")
    return content.strip()


def compress(
    messages: list[dict],
    preserve_recent: int = PRESERVE_RECENT,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
    min_turns_to_compress: int = 6,
) -> list[dict]:
    """Compress an OpenAI-format messages array while preserving conversational state.

    Args:
        messages: List of dicts with "role" and "content" keys.
        preserve_recent: Number of recent user/assistant turn pairs to keep verbatim.
        model: Ollama model to use for summarization.
        ollama_url: Ollama API endpoint.
        min_turns_to_compress: Don't compress if fewer than this many messages.

    Returns:
        Compressed messages list in the same OpenAI format.
    """
    if not messages:
        return []

    # Count actual user/assistant turns, not total messages
    n_turns = sum(1 for m in messages if m.get("role") in ("user", "assistant")) // 2
    if n_turns < min_turns_to_compress:
        return list(messages)

    # Separate system prompt from conversation
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conv_msgs = [m for m in messages if m.get("role") != "system"]

    if not conv_msgs:
        return list(messages)

    # Split: history to compress vs recent turns to preserve
    # preserve_recent refers to turn pairs, so preserve_recent*2 messages
    preserve_count = preserve_recent * 2
    if len(conv_msgs) <= preserve_count:
        return list(messages)

    history_msgs = conv_msgs[:-preserve_count]
    recent_msgs = conv_msgs[-preserve_count:]

    # Format history for summarization
    history_text = "\n".join(
        f"[{m['role'].upper()}]: {m.get('content', '')}" for m in history_msgs
    )

    # Compress via local model
    summary = _summarize_via_ollama(history_text, model=model, ollama_url=ollama_url)

    # Build compressed messages
    compressed = []

    # Keep system prompt(s)
    compressed.extend(system_msgs)

    # Insert scaffold summary as a system message
    compressed.append({
        "role": "system",
        "content": (
            f"[SCAFFOLD STATE — compressed from {len(history_msgs)} earlier messages]\n"
            f"{summary}"
        ),
    })

    # Keep recent turns verbatim
    compressed.extend(recent_msgs)

    return compressed
