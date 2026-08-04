# langstate — current maintenance backlog

## Current product boundary

`langstate` is an alpha library that asks a configured local or cloud model to
compress older OpenAI-format messages into a scaffold state. It preserves the
system message and recent message suffix, and its lexical `validate` helper can
check caller-supplied literal facts. Compression quality is model- and
input-dependent; it is not a guarantee that all state survives.

## Next maintenance slices

- Add `required_facts=` and fail-closed return-original behavior to `compress`.
- Treat empty output, adapter failure, missing required facts, and non-positive
  token reduction as explicit failed receipts.
- Define preservation semantics for tool, function, developer, and irregular
  message roles rather than describing positional messages as turn-pairs.
- Make live Ollama tests opt-in by marker and add Ruff to the declared CI gate.
- Replace approximate character counts with an explicitly selected tokenizer.
- Remove root/source duplicates so `src/langstate` is authoritative.
- Build a held-out, independently labeled fidelity corpus with contradiction,
  survival, compression, latency, and cost measurements per adapter.

## Evidence rule

Keep retired research framing and superseded quantitative marketing out of
active product guidance. Benchmark statements must name their corpus, model,
denominator, receipt, and observed failures.
