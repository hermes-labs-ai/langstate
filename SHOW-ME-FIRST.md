# langstate — show the contract first

`langstate` turns the older part of an OpenAI-format conversation into a
visible scaffold message while retaining the system prompt and a recent suffix.
The useful part is inspectability: you can ask whether named literal facts are
still present before sending the compressed list onward.

This deterministic example exercises that contract without requiring a model:

```bash
PYTHONPATH=src python3 - <<'PY'
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

def summary(_prompt):
    return "- Budget is $4,000.\n- Launch is May 5.\n- Dana owns the release."

compressed = compress(messages, preserve_recent=2, summarizer=summary)
receipt = validate(messages, compressed, facts=["$4,000", "May 5", "Dana"])
print(compressed[1]["content"])
print(receipt.as_dict())
PY
```

The output contains a `[SCAFFOLD STATE]` system message and a receipt with the
three requested strings in `survived`. The injected summarizer is deliberate:
it demonstrates the API and receipt deterministically. Replace it with the
default local Ollama path or an adapter when evaluating a real model.

The summary is lossy. `validate` is a lexical check, not proof that a model
understood or faithfully paraphrased a conversation. Use raw messages when
exact replay or structured state is required.
