# Changelog

## [0.2.0] - 2026-07-17

Supersedes 0.1.0 on PyPI. Internal iterations happened between public
releases; this release adopts the highest coherent number rather than
re-issuing intermediate ones (an internal 0.1.1 was prepared but never
published — its notes are folded in here).

### Added
- `validate(before, after)` — deterministic, zero-dependency receipt proving
  which selected literal strings still occur after compression (`Receipt.ok`,
  `.survival_rate`, `.summary()`). Runs in CI, no model call; it is not semantic
  validation.
- Top-level exports for `validate`, `Receipt`, `extract_facts`, and
  `__version__`.

### Changed
- The direct local adapter default changes from qwen3:14b to qwen3:4b. The
  `compress()` default was already qwen3:4b in public 0.1.0.
- The direct Anthropic adapter default changes from claude-opus-4-7 to
  claude-haiku-4-5-20251001.
- Documentation describes the LPCI approach in plain terms; earlier
  benchmark framing that did not meet our evidence bar was removed.

### Compatibility
- `compress()` keeps the public 0.1.0 signature and runtime implementation;
  release-readiness edits only bound its docstring claims.
- Adapters were already shipped and documented in public 0.1.0; 0.2.0 changes
  defaults rather than adding the adapter module.

### Removed
- The internal `te_check.py` benchmark helper is no longer part of the
  shipped package (it was never public API and carried project-specific test
  fixtures). Packaging now prunes `tests/`, `bench/`, and internal
  workspaces from the sdist.

## [0.1.0] - 2026-04-26

First public release. `compress(messages)`.

- Scaffold-aware context compression for OpenAI-format messages
- Local, OpenAI, and Anthropic summarizer adapters plus custom callables
- Preserves system prompts and recent turns verbatim; compresses older history
  into a `[SCAFFOLD STATE]` summary
- 51-54% token reduction on typical conversations
- Apache-2.0, zero runtime dependencies (stdlib only)
