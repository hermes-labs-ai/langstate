"""
langstate.compress — Scaffold-aware context compression for OpenAI-format messages.

Compresses older conversation history into a state-oriented scaffold summary,
keeping the system prompt and recent turns verbatim. By default it uses a local
Ollama model (qwen3:4b), which requires local compute.

Usage:
    from langstate.compress import compress
    compressed = compress(messages)
    response = client.chat.completions.create(messages=compressed, model="gpt-4o")
"""

from typing import Callable, Optional

from langstate import adapters as _adapters

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3:4b"
PRESERVE_RECENT = 4  # keep last N user/assistant turns verbatim

Summarizer = Callable[[str], str]


def _count_tokens_approx(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return len(text) // 4


def _count_messages_tokens(messages: list[dict]) -> int:
    """Approximate total tokens across all messages."""
    return sum(_count_tokens_approx(m.get("content", "")) for m in messages)


def _build_compression_prompt(text: str) -> str:
    """The scaffold compression instruction shared by every adapter."""
    return (
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


def compress(
    messages: list[dict],
    preserve_recent: int = PRESERVE_RECENT,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
    min_turns_to_compress: int = 6,
    summarizer: Optional[Summarizer] = None,
) -> list[dict]:
    """Compress older messages while keeping system and configured recent turns verbatim.

    Args:
        messages: List of dicts with "role" and "content" keys.
        preserve_recent: Number of recent user/assistant turn pairs to keep verbatim.
        model: Ollama model to use when no summarizer is given (back-compat).
        ollama_url: Ollama API endpoint (back-compat).
        min_turns_to_compress: Don't compress if fewer than this many messages.
        summarizer: Optional ``summarize(prompt) -> str`` callable. If None, falls back
            to a local Ollama adapter (qwen3:4b) for back-compat with the MVP.

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

    # Compress via the chosen summarizer (default: local Ollama, MVP back-compat)
    if summarizer is None:
        summarizer = _adapters.ollama(model=model, url=ollama_url)
    summary = summarizer(_build_compression_prompt(history_text))

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
