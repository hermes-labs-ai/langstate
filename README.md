# langstate

**Compress long LLM conversations into visible working state — then check that
the literal facts you care about survived.**

`langstate` is a small experimental Python library for OpenAI-format message
lists. It keeps system messages and recent turns verbatim, summarizes older
history into a visible `[SCAFFOLD STATE]` system message, and returns the same
list-shaped interface that chat clients already accept.

Most context compression gives you a summary and asks you to trust it.
LangState makes that lossy step inspectable: the compressed state is an ordinary
message you can view, log, edit, replace, or reject. `validate(...)` then gives
you a deterministic receipt for the literal facts you name explicitly.

This is a functional prototype/library, not a lossless archive, a structured
state store, or production infrastructure. Summary quality depends on the
model and the input; treat `validate` as a narrow check, not a guarantee of
semantic fidelity.

## Install

```bash
python -m pip install langstate
```

Python 3.10+; no runtime dependencies beyond the standard library. The default
summarizer calls a local [Ollama](https://ollama.ai) model, so prepare it once:

```bash
ollama pull qwen3:4b
```

## Try it in two minutes

This deterministic example produces a real scaffold and receipt without a model
call. It injects a tiny summarizer so the result is reproducible; remove
`summarizer=demo_summary` afterward to use local Ollama instead.

```python
from langstate import compress, validate

messages = [{"role": "system", "content": "Be concise."}]
for user, assistant in [
    (
        "We are launching the developer preview on May 5. Keep the rollout "
        "private until the invitation list is approved, and cap the launch "
        "budget at $4,000.",
        "Understood. I will treat May 5, a private preview, and the $4,000 "
        "cap as launch constraints.",
    ),
    (
        "Dana owns the release checklist. Morgan owns the API migration. "
        "The only blocker is the billing webhook retry bug in staging.",
        "I recorded Dana as release owner, Morgan as migration owner, and "
        "the staging billing webhook as the blocker.",
    ),
    (
        "The first cohort is 25 developers using Python clients. We will not "
        "invite JavaScript users until the second week.",
        "The first cohort is 25 Python developers; JavaScript waits until week two.",
    ),
    (
        "If the blocker is still open on May 3, move the preview to May 12 "
        "rather than cutting the verification pass.",
        "Unresolved on May 3 means move to May 12, never skip verification.",
    ),
    ("What should the launch note emphasize?", "The private, Python-first preview."),
    ("Who gives final approval?", "Dana, after webhook verification passes."),
]:
    messages.extend(({"role": "user", "content": user},
                     {"role": "assistant", "content": assistant}))

def demo_summary(_prompt):
    return (
        "- Preview: May 5; budget cap: $4,000.\n"
        "- Dana owns release; Morgan owns API migration.\n"
        "- Blocker: staging billing webhook retries.\n"
        "- If still blocked May 3, move to May 12."
    )

compressed = compress(messages, preserve_recent=2, summarizer=demo_summary)

receipt = validate(
    messages,
    compressed,
    facts=["May 5", "$4,000", "Dana", "Morgan", "May 12"],
)
assert receipt.ok
print(compressed[1]["content"])
print(receipt.summary())
```

The result makes the compressed state visible before you send it anywhere:

```text
[SCAFFOLD STATE — compressed from 8 earlier messages]
- Preview: May 5; budget cap: $4,000.
- Dana owns release; Morgan owns API migration.
- Blocker: staging billing webhook retries.
- If still blocked May 3, move to May 12.

5/5 facts survived (100%) · 62% smaller
```

Now omit `summarizer=demo_summary` after preparing Ollama to judge a real local
model against the facts your application actually needs.
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
