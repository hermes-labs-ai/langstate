# Changelog

## v0.1.0 — 2026-04-17

Initial version. `compress(messages)` with Ollama backend.

- Scaffold-aware context compression for OpenAI-format messages
- Preserves system prompts and recent turns verbatim
- Compresses older conversation history via local Ollama model (qwen3:4b)
- 51-54% compression ratio on typical conversations
- Zero-cost summarization (local model, no API calls)
