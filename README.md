# langstate

**Turn older chat history into an explicit, inspectable scaffold — then check the
literal facts your application cannot afford to lose.**

`langstate` is a small experimental Python library for OpenAI-format message
lists. It keeps system messages and a recent conversation suffix verbatim,
summarizes older messages into a visible `[SCAFFOLD STATE]` system message, and
returns the same list-shaped interface that chat clients already accept.

Its distinctive move is not to call a summary “memory.” It makes the compressed
working state an ordinary message you can inspect, log, replace, or reject.
`validate(...)` then gives a deterministic lexical receipt for the facts you
name explicitly.

This is a functional prototype/library, not a lossless archive, a structured
state store, or production infrastructure. Summary quality depends on the
model and the input; treat `validate` as a narrow check, not a guarantee of
semantic fidelity.

## Install

For the currently released PyPI package:

```bash
python -m pip install langstate
```

To exercise the current repository source directly, install a checkout instead:

```bash
python -m pip install .
```

PyPI `0.2.0` is installable, but its published project metadata predates the
current repository framing. Because PyPI releases are immutable, a later
new-version release is required before the project page reflects this README
and metadata.

Python 3.10+; no runtime dependencies beyond the standard library. The default
summarizer calls a local [Ollama](https://ollama.ai) model, so prepare it once:

```bash
ollama pull qwen3:4b
```

## First useful result

This six-turn deterministic example produces a scaffold and receipt without
requiring a model. The system prompt and the last two user/assistant pairs remain
verbatim because it sets `preserve_recent=2`.

```python
from langstate import compress, validate

messages = [{"role": "system", "content": "Be concise."}]
for user, assistant in [
    ("Budget is $4,000.", "Noted."),
    ("Launch is May 5.", "Noted."),
    ("Dana owns the release.", "Noted."),
    ("Any risks?", "Check the budget and date."),
    ("What should ship?", "The API client."),
    ("Anything else?", "No."),
]:
    messages.extend(({"role": "user", "content": user},
                     {"role": "assistant", "content": assistant}))

def demo_summary(_prompt):
    return "- Budget is $4,000.\n- Launch is May 5.\n- Dana owns the release."

compressed = compress(messages, preserve_recent=2, summarizer=demo_summary)

receipt = validate(
    messages,
    compressed,
    facts=["$4,000", "May 5", "Dana"],
)
assert receipt.ok
print(len(messages), "messages ->", len(compressed), "messages")
print(receipt.summary())
```

The observed deterministic result is `13 messages -> 6 messages` with `3/3`
selected facts surviving. To try a real model, omit `summarizer=demo_summary`
after preparing Ollama, then judge the returned receipt for your own facts.
`Receipt.ok` is true only when every requested string occurs in the compressed
messages after case-and-whitespace normalization. It cannot credit a paraphrase,
so it is intentionally conservative. Use explicit `facts=[...]` for a focused
contract; automatic fact extraction is a convenience heuristic.

## How it works

For conversations of at least six user/assistant turns, `compress`:

1. retains all `system` messages and the requested recent suffix verbatim;
2. sends the older non-system messages to the selected summarizer;
3. inserts that result as `[SCAFFOLD STATE — compressed from N earlier messages]`;
4. returns the resulting OpenAI-format list.

You can use the result with an OpenAI-compatible chat client, or keep the
scaffold as an auditable intermediate artifact. The library does not make a
semantic preservation claim about the model-generated summary.

## Choose a summarizer

| Option | Default/model | What you provide |
|---|---|---|
| Local | Ollama `qwen3:4b` | Ollama at `localhost:11434` |
| OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| Custom | `(prompt: str) -> str` | Your callable |

```python
from langstate import compress
from langstate.adapters import build

local = compress(messages)
openai = compress(messages, summarizer=build("openai"))
anthropic = compress(messages, summarizer=build("anthropic"))
custom = compress(messages, summarizer=my_summarizer)
```

Use `probe(name)` to see whether a configured adapter is currently usable.

## Boundaries and current evidence

- The library’s deterministic tests cover message shaping, injected
  summarizers, adapter-unavailable errors, lexical receipts, and version
  consistency. They do not establish the quality of any live model.
- Repository benchmark JSON files record single, synthetic-corpus runs for the
  named adapter and model. They are leads for model selection, not general
  performance claims.
- `validate` checks literal text only. It neither establishes semantic
  equivalence nor detects an invented claim that happens to reuse a checked
  phrase.
- Use original messages for exact replay, regulated records, tool-call
  semantics, or any workflow where a lossy summary is unacceptable.

## API

```python
compress(
    messages,
    preserve_recent=4,
    min_turns_to_compress=6,
    model="qwen3:4b",
    summarizer=None,
)

validate(before, after, facts=None)
```

See `Receipt.as_dict()` for a JSON-friendly receipt. The package is
Apache-2.0 licensed.
