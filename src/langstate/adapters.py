"""
langstate.adapters — production backends for the scaffold summarizer.

Each adapter is a callable ``summarize(prompt: str) -> str`` that takes the
composed compression prompt and returns a natural-language scaffold summary.

Adapters are stdlib-only (urllib) to preserve the "zero heavy deps" promise
of langstate. API keys are read from the environment, not arguments —
adapters raise ``AdapterUnavailable`` when their key or backend is missing
so callers can gracefully degrade to the local adapter.

Production targets (one cheap default per provider, per the Hermes spec):
    - Anthropic: claude-haiku-4-5          (env ANTHROPIC_API_KEY)
    - OpenAI:    gpt-4o-mini               (env OPENAI_API_KEY)
    - Local:     qwen3:4b via Ollama       (no key, localhost:11434) — the default
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

Summarizer = Callable[[str], str]


class AdapterUnavailable(RuntimeError):
    """Raised when an adapter cannot run (missing key, unreachable, etc.)."""


# ---------------------------------------------------------------------------
# Ollama (local, default)
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_LOCAL_MODEL = "qwen3:4b"  # small, fast, zero-cost; the library-wide default


def ollama(
    model: str = DEFAULT_LOCAL_MODEL,
    url: str = OLLAMA_URL,
    num_predict: int = 8000,
    temperature: float = 0.2,
    timeout: int = 600,
) -> Summarizer:
    """Build a summarizer that calls a local Ollama model."""

    def _call(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "Respond directly. Do not think or reason. Just output the summary."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": temperature},
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
        except (urllib.error.URLError, OSError) as e:
            raise AdapterUnavailable(f"ollama unreachable at {url}: {e}") from e
        content = (result.get("message") or {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty content. Increase num_predict.")
        return content

    return _call


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def openai(
    model: str = DEFAULT_OPENAI_MODEL,
    api_key: Optional[str] = None,
    url: str = OPENAI_URL,
    max_tokens: int = 4000,
    temperature: float = 0.2,
    timeout: int = 120,
) -> Summarizer:
    """Build a summarizer that calls the OpenAI chat completions API."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise AdapterUnavailable("OPENAI_API_KEY not set")

    def _call(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "Respond directly. Do not think or reason. Just output the summary."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise AdapterUnavailable(f"openai HTTP {e.code}: {body[:200]}") from e
        except (urllib.error.URLError, OSError) as e:
            raise AdapterUnavailable(f"openai unreachable: {e}") from e
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"openai unexpected response: {result}") from e

    return _call


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_VERSION = "2023-06-01"


def anthropic(
    model: str = DEFAULT_ANTHROPIC_MODEL,
    api_key: Optional[str] = None,
    url: str = ANTHROPIC_URL,
    max_tokens: int = 4000,
    temperature: float = 0.2,
    timeout: int = 120,
) -> Summarizer:
    """Build a summarizer that calls the Anthropic messages API."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AdapterUnavailable("ANTHROPIC_API_KEY not set")

    def _call(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": "Respond directly. Do not think or reason. Just output the summary.",
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise AdapterUnavailable(f"anthropic HTTP {e.code}: {body[:200]}") from e
        except (urllib.error.URLError, OSError) as e:
            raise AdapterUnavailable(f"anthropic unreachable: {e}") from e
        blocks = result.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        if not text:
            raise RuntimeError(f"anthropic returned no text blocks: {result}")
        return text

    return _call


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY = {
    "local":     ("qwen3:4b (Ollama)",           ollama),
    "openai":    ("gpt-4o-mini",                 openai),
    "anthropic": ("claude-haiku-4-5",            anthropic),
}


def build(name: str) -> Summarizer:
    """Build a summarizer by name. Raises AdapterUnavailable if not usable."""
    if name not in REGISTRY:
        raise ValueError(f"unknown adapter {name!r}. choices: {list(REGISTRY)}")
    _, factory = REGISTRY[name]
    return factory()


def probe(name: str) -> dict:
    """Check whether an adapter is usable; return {available, reason, latency_ms}."""
    t0 = time.time()
    try:
        fn = build(name)
        out = fn("Say OK.")
    except AdapterUnavailable as e:
        return {"name": name, "available": False, "reason": str(e), "latency_ms": None}
    except Exception as e:  # noqa: BLE001
        return {"name": name, "available": False, "reason": f"{type(e).__name__}: {e}", "latency_ms": None}
    return {
        "name": name,
        "available": True,
        "reason": "ok",
        "latency_ms": int((time.time() - t0) * 1000),
        "sample": out[:80],
    }
