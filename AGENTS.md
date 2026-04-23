# AGENTS.md — langstate

`langstate` is a scaffold-aware context compression library for OpenAI-format
messages. Single public function: `compress(messages) -> messages`. Backed by
the LPCI thesis: stateless LLMs hold state via language scaffold, TE approximately
zero (Markov property).

## Use it for

- compressing long agent conversations before passing to any OpenAI-compatible API
- reducing token costs in production multi-turn pipelines
- running local-first compression (Ollama) with no API costs

## Do not use it for

- conversations under 6 turns (compression is skipped automatically)
- paths requiring exact verbatim history
- real-time inference where compression latency is a concern

## Repository layout

```
src/langstate/          Package source
  __init__.py           Re-exports compress
  compress.py           Single public function: compress()
  adapters.py           Ollama / OpenAI / Anthropic summarizer backends
  te_check.py           Transfer-entropy proxy benchmark (research utility)
tests/                  Pytest suite (13 tests)
  test_compress.py      Format, compression ratio, state preservation
  test_adapters.py      Adapter protocol + registry + network-free integration
```

## Minimal commands

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

Requires Ollama running locally with qwen3:4b or qwen3:14b pulled for Ollama-backed tests.

## Output shape

- `compress(messages)` returns a shorter list in the same OpenAI format
- System prompts preserved verbatim
- Last 4 turn-pairs preserved verbatim
- Older turns → `[SCAFFOLD STATE — compressed from N earlier messages]\n<summary>` system message

## Success means

- 13/13 tests pass
- `compress(make_messages(20))` returns fewer tokens with state facts preserved
- `compress(make_messages(5))` returns input unchanged (below threshold)

## Adapters

Three production adapters in `src/langstate/adapters.py`:
- `local` — qwen3:14b via Ollama (no key, zero cost)
- `openai` — gpt-4o-mini (env OPENAI_API_KEY)
- `anthropic` — claude-opus-4-7 (env ANTHROPIC_API_KEY)

Any callable `(prompt: str) -> str` works as a custom summarizer.

## Relationship to research

- `langquant` (roli-lpci/langquant) — the LPCI proof, TE≈0, Markov sufficiency
- `langquant-sdk` (private) — TS prototypes: scaffold-monad, driftwatch, computetrace
