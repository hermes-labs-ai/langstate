# langstate — TODO

## What this is
LLM-based semantic compression for OpenAI-format message arrays. Preserves conversational state (facts, decisions, task state) while reducing token count ~50-55%. Uses local Ollama model (qwen3:4b) for zero API cost.

## Status: MVP DONE
- `compress(messages)` works, 6/6 tests pass
- 51.2% compression on 20 turns, 54.3% on 25 turns
- State preservation verified: key facts survive compression

## Integration with langquant-sdk
langquant-sdk already has scaffold-monad, driftwatch, and computetrace — all passing (94 tests total). langstate's `compress()` fills the known gap: **LLM-based semantic compression** to replace scaffold-monad's structural compress (key-dropping + truncation).

### Integration path:
1. Port `compress()` logic into `langquant-sdk/scaffold-monad/src/compressor.ts` as an alternative compressor
2. Or: keep langstate as standalone Python package, langquant-sdk as TypeScript package — both valid
3. Decision: Python-first (langstate) for PyPI distribution, TS port later for langquant-sdk

## Immediate TODOs (next session)

### Ship
- [ ] Add `pyproject.toml` for PyPI packaging
- [ ] `pip install langstate` should work
- [ ] Write 1-paragraph README with usage example
- [ ] Push to GitHub as `roli-lpci/langstate` (private initially)

### Harden
- [ ] Add `validate(messages_before, messages_after)` function — measures state sufficiency post-compression using TE≈0 methodology (the marketing hook)
- [ ] Handle edge cases: messages with images/tool_calls, non-string content
- [ ] Make model configurable at runtime (default qwen3:4b, allow any Ollama model)
- [ ] Add retry logic for Ollama timeouts
- [ ] Benchmark: measure actual token savings via tiktoken, not just char-based approximation

### Research backlog (from 530MB corpus analysis)
- [ ] Test compression at different ratios (target_ratio parameter)
- [ ] Compare with LLMLingua (syntactic pruning) on same inputs
- [ ] Measure TE on compressed vs uncompressed scaffold — formal validation
- [ ] Cognitive load scoring (Miller's 7±2 chunks) on compressed output
- [ ] Code vs NL substrate routing (SubstrateRouter idea)

## Architecture notes
- Single function, no server, no auth, no framework dependency
- Input/output: OpenAI chat format (list of dicts with role + content)
- System prompt always preserved verbatim
- Last N turn-pairs preserved verbatim (default: 4 pairs = 8 messages)
- Everything else compressed into a [SCAFFOLD STATE] system message
- Compression prompt is scaffold-aware: preserves facts, decisions, state — not generic summarization

## Relationship to other projects
| Project | Relationship |
|---------|-------------|
| langquant | The LPCI proof (TE≈0, 2.5x compression) — langstate is the productization |
| langquant-sdk | TS prototypes (scaffold-monad, driftwatch, computetrace) — langstate is the Python complement |
| cogito-ergo | Memory retrieval — could use langstate compression on stored memories |
| OpenClaw | AI agent — insert langstate at 70% context fill |
| Browser LLM | Caption compression before local model ingestion |
