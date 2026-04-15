# AGENTS.md — langstate

## What this project is
LLM-based semantic compression for OpenAI-format message arrays. Single Python function: `compress(messages) -> messages`. Uses local Ollama (qwen3:4b) for zero API cost. Preserves conversational state while reducing tokens ~50-55%.

## Key files
- `compress.py` — the entire library. One public function: `compress()`. ~130 lines.
- `test_compress.py` — 6 test cases covering empty, 1-turn, 5-turn, 20-turn, 25-turn, and state preservation.
- `__init__.py` — re-exports `compress` from `compress.py`.

## How it works
1. System prompt(s) kept verbatim
2. Last 4 turn-pairs (8 messages) kept verbatim
3. Everything else formatted as `[ROLE]: content` and sent to local Ollama for scaffold-aware summarization
4. Summary inserted as a `[SCAFFOLD STATE]` system message
5. Output is valid OpenAI chat format

## Running tests
```bash
cd ~/Documents/projects/langstate
python3 test_compress.py
```
Requires Ollama running locally with qwen3:4b loaded.

## Dependencies
- Python 3.10+
- Ollama running at localhost:11434 with qwen3:4b
- No pip dependencies (uses only stdlib: json, urllib)

## Design constraints
- No paid APIs — local Ollama only
- No framework dependencies — stdlib only
- No server/CLI — library function only
- Correctness first, speed later
- Scaffold-aware: preserves facts, decisions, task state — not generic summarization

## Backed by
LPCI thesis (roli-lpci/langquant): stateless LLMs hold state via language scaffold, TE≈0 (Markov property), 2.5x compression. This function is the productization of that proof.

## Related repos
- `langquant` — the LPCI proof
- `langquant-sdk` — TS prototypes (scaffold-monad, driftwatch, computetrace)
- Research corpus at `~/Desktop/llm-scaffold-research/` (530MB, 1401 files)
