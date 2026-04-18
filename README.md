# langstate

Scaffold-aware context compression for OpenAI-format messages. Compresses conversation history via a local Ollama model at zero cost (no API calls).

## What it does

`compress(messages)` takes an OpenAI-format messages array and returns a shorter one that preserves all conversational state:

- System prompts kept verbatim
- Recent turns (last 4 pairs) kept verbatim
- Older turns compressed into a scaffold state summary via local model
- 51-54% compression ratio on typical conversations

All facts, decisions, preferences, and task state are preserved in the compressed summary.

## Usage

```python
from langstate.compress import compress

# Standard OpenAI-format messages
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    # ... many turns ...
]

compressed = compress(messages)
# Pass compressed messages to any OpenAI-compatible API
response = client.chat.completions.create(messages=compressed, model="gpt-4o")
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running locally

```bash
ollama pull qwen3:4b
```

## Configuration

```python
compress(
    messages,
    preserve_recent=4,          # turn pairs to keep verbatim
    model="qwen3:4b",           # Ollama model for summarization
    min_turns_to_compress=6,    # minimum turns before compression kicks in
)
```

## License

Apache 2.0
