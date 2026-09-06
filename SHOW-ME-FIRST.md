# langstate — show the contract first

`langstate` turns the older part of an OpenAI-format conversation into a
visible scaffold message while retaining the system prompt and a recent suffix.
The useful part is inspectability: you can ask whether named literal facts are
still present before sending the compressed list onward.

Exercise that contract without a model, network call, API key, or Ollama:

```bash
python -m pip install langstate==0.2.3
langstate demo
```

The JSON output contains a `[SCAFFOLD STATE]` system message and a successful
receipt for `Project: Atlas` and `Budget: $4,000`. The command uses an injected
deterministic summarizer. Use the default local Ollama path or an adapter when
evaluating a real model.

The summary is lossy. `validate` is a lexical check, not proof that a model
understood or faithfully paraphrased a conversation. Use raw messages when
exact replay or structured state is required.
