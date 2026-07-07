# Changelog

## v0.1.1

Supersedes v0.1.0 on PyPI. Packaging and documentation correction — no API change.

- Removed the internal `te_check.py` benchmark helper from the shipped package
  (it was never part of the public API and carried project-specific test
  fixtures). The compression and receipt code is unchanged.
- Documentation no longer references a transfer-entropy figure; the README and
  `llms.txt` now describe the LPCI approach in plain terms.
- Generic example values in the `validate` docstring.

## v0.1.0

First public release. `compress(messages)` plus a facts-survived receipt.

- Scaffold-aware context compression for OpenAI-format messages
- Preserves system prompts and recent turns verbatim; compresses older history
  into a `[SCAFFOLD STATE]` summary
- 51-54% token reduction on typical conversations
- `validate(before, after)` — deterministic, zero-dependency receipt proving
  which facts survived compression (`Receipt.ok`, `.survival_rate`, `.summary()`)
- Pluggable summarizers: `local` (qwen3:4b via Ollama, default, zero-cost),
  `openai` (gpt-4o-mini), `anthropic` (claude-haiku-4-5), or any callable
- Default compression model unified to `qwen3:4b` across the library
- Apache-2.0, zero runtime dependencies (stdlib only)
