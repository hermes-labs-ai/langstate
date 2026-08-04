# Changelog

## [0.2.1] - 2026-08-04

### Changed
- Present LangState as an experimental, inspectable context-compression library:
  older history becomes visible scaffold state rather than opaque “memory.”
- Add a reproducible first-use walkthrough with the emitted scaffold and lexical
  fact-survival receipt.
- Describe conversation expansion as “larger” instead of reporting a negative
  “smaller” percentage.
- Remove unsupported completeness, semantic-preservation, benchmark, and
  production-readiness claims from public-facing package materials.
- Add tag-checked PyPI Trusted Publishing for the `0.2.1` release.

## [0.2.0] - 2026-07-17

Supersedes 0.1.0 on PyPI. Internal iterations happened between public
releases; this release adopts the highest coherent number rather than
re-issuing intermediate ones (an internal 0.1.1 was prepared but never
published — its notes are folded in here).

### Added
- `validate(before, after)` — deterministic, zero-dependency receipt reporting
  which selected facts remain lexically present (`Receipt.ok`, `.survival_rate`,
  `.summary()`). Runs in CI, no model call.
- Pluggable summarizer adapters: `local` (qwen3:4b via Ollama, default,
  zero-cost), `openai` (gpt-4o-mini), `anthropic` (claude-haiku-4-5), or any
  callable.
- src/ layout and CI test workflow (pytest, Python 3.10-3.12).

### Changed
- Default compression model unified to `qwen3:4b` across compress and
  adapters.
- Documentation describes the LPCI approach in plain terms; earlier
  benchmark framing that did not meet our evidence bar was removed.

### Removed
- The internal `te_check.py` benchmark helper is no longer part of the
  shipped package (it was never public API and carried project-specific test
  fixtures). Packaging now prunes `tests/`, `bench/`, and internal
  workspaces from the sdist.

## [0.1.0] - 2026-04-26

First public release. `compress(messages)`.

- Scaffold-aware context compression for OpenAI-format messages
- Preserves system prompts and recent turns verbatim; compresses older history
  into a `[SCAFFOLD STATE]` summary
- Shortens older history while keeping system prompts and recent turns verbatim
- Apache-2.0, zero runtime dependencies (stdlib only)
