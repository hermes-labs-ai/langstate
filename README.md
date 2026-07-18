# langstate

`langstate` compresses older OpenAI-format conversation messages into a scaffold summary while preserving system messages and a configurable number of recent turns verbatim. Retention and size reduction depend on the conversation and summarizer.

`validate()` can record whether selected literal strings appear in the compressed output. It is deterministic and makes no model call, but it is a lexical check rather than a semantic-equivalence test.

## What it does

```python
from langstate import compress

compressed = compress(messages)
# Same OpenAI message shape; inspect retention before using the result
response = client.chat.completions.create(messages=compressed, model="gpt-4o")
```

The output is a valid OpenAI-format messages list:
- System prompts kept verbatim
- Last 4 turn-pairs kept verbatim
- Older turns compressed into a `[SCAFFOLD STATE]` system message via local or cloud model

## Check selected literals — the receipt

`validate` returns a deterministic lexical receipt and makes no model call:

```python
from langstate import compress, validate

compressed = compress(messages)

# Check the specific facts you care about:
receipt = validate(messages, compressed,
                   facts=["$4,000 budget", "launch May 5", "Dana"])

print(receipt.summary())   # counts literal strings found and approximate size change
print(receipt.dropped)     # selected strings not found in the output
assert receipt.ok          # optional gate on exact lexical retention

# Or heuristically select tokens (numbers, money, acronyms, names):
receipt = validate(messages, compressed)
```

A green receipt means only that the selected normalized strings occur in the
output. It does not verify meaning, attribution, negation, completeness, or
semantic equivalence. Auto-extraction is heuristic; pass an explicit `facts=`
list for controlled checks. `receipt.as_dict()` gives a JSON-friendly record to
log.

## Install

```bash
python -m pip install 'langstate==0.2.0'
```

Requirements: Python 3.10+, no heavy dependencies (stdlib only). For local summarization, run [Ollama](https://ollama.ai) locally:

```bash
ollama pull qwen3:4b
```

## Adapters

langstate ships three built-in summarizer backends:

| Adapter | Model | Cost | Key |
|---|---|---|---|
| `local` (default) | qwen3:4b via Ollama | local compute | none |
| `openai` | gpt-4o-mini | API | `OPENAI_API_KEY` |
| `anthropic` | claude-haiku-4-5-20251001 | API | `ANTHROPIC_API_KEY` |

```python
from langstate import compress
from langstate.adapters import build

# Local Ollama (default, no API key; uses local compute)
compressed = compress(messages)

# OpenAI
compressed = compress(messages, summarizer=build("openai"))

# Anthropic
compressed = compress(messages, summarizer=build("anthropic"))

# Any callable (prompt: str) -> str
compressed = compress(messages, summarizer=my_summarizer)
```

## Configuration

```python
compress(
    messages,
    preserve_recent=4,         # turn-pairs to keep verbatim (default: 4)
    min_turns_to_compress=6,   # skip compression for short conversations (default: 6)
    model="qwen3:4b",          # Ollama model when no summarizer is given
    summarizer=None,           # custom callable: (prompt: str) -> str
)
```

## Choosing a model

**The default is local `qwen3:4b` via Ollama.** It requires a model download and
local compute but no API key. Compression quality depends on the model and data;
use explicit lexical checks plus an evaluation appropriate to the consequences
of semantic errors.

Pick by what you're optimizing:

| Want | Use | Trade-off |
|---|---|---|
| No provider key | `local` — qwen3:4b (default) | requires Ollama, a model download, and local compute |
| OpenAI stack | `openai` — gpt-4o-mini | requires `OPENAI_API_KEY`; evaluate on your data |
| Anthropic stack | `anthropic` — claude-haiku-4-5-20251001 | requires `ANTHROPIC_API_KEY`; evaluate on your data |
| Full control | your own `summarizer=` | any `(prompt: str) -> str` callable |

Switching is one argument:

```python
compress(messages)                              # local qwen3:4b (default)
compress(messages, model="qwen3:14b")           # alternate local model; evaluate on your data
compress(messages, summarizer=build("openai"))  # optional provider adapter
```

No bundled result establishes a universal quality ranking. Evaluate summarizers
on representative traffic, and pass `model=` explicitly when behavior stability
matters.

## Adapter probe

```python
from langstate.adapters import probe, REGISTRY

for name in REGISTRY:
    print(probe(name))
# {"name": "local", "available": True, "latency_ms": 423, ...}
# {"name": "openai", "available": False, "reason": "OPENAI_API_KEY not set", ...}
```

## License

Apache-2.0

---

## About Hermes Labs

Hermes Labs builds AI audit infrastructure for teams deploying AI agents in regulated environments.
All tools are released as open-source software — MIT or Apache-2.0, no SaaS tier.
The audit work is paid; the code is not.

**hermes-labs.ai**

### OSS audit stack

| Layer | Tool | Description |
|---|---|---|
| Static audit | [lintlang](https://github.com/hermes-labs-ai/lintlang) | Agent-config static lint (HERM + H1-H7) |
| Static audit | [rule-audit](https://github.com/hermes-labs-ai/rule-audit) | Rule-logic audit: contradictions + gaps |
| Static audit | scaffold-lint | Scaffold budget + technique stacking |
| Static audit | [intent-verify](https://github.com/hermes-labs-ai/intent-verify) | Spec-drift checks |
| Runtime observability | [little-canary](https://github.com/hermes-labs-ai/little-canary) | Prompt injection detection |
| Runtime observability | [agent-warden](https://github.com/hermes-labs-ai/agent-warden) | Runtime policy guard |
| Runtime observability | [colony-probe](https://github.com/hermes-labs-ai/colony-probe) | Prompt confidentiality audit |
| Regression & scoring | [hermes-jailbench](https://github.com/hermes-labs-ai/hermes-jailbench) | Jailbreak regression benchmark |
| Regression & scoring | [agent-convergence-scorer](https://github.com/hermes-labs-ai/agent-convergence-scorer) | N-agent output consistency |
| Supporting infra | [claude-router](https://github.com/hermes-labs-ai/claude-router) | Model-tier + scaffold router |
| Supporting infra | [quickthink](https://github.com/hermes-labs-ai/quickthink) | Compressed planning scaffold for local LLMs |
| Supporting infra | [langstate](https://github.com/hermes-labs-ai/langstate) | Scaffold-aware context compression |
| Supporting infra | [agent-gorgon](https://github.com/hermes-labs-ai/agent-gorgon) | Tool-fabrication defense for Claude Code |
| Supporting infra | [zer0dex](https://github.com/hermes-labs-ai/zer0dex) | Dual-layer agent memory |
| Supporting infra | [forgetted](https://github.com/hermes-labs-ai/forgetted) | Mid-conversation incognito |
| Dev tools | repo-audit | Launch-readiness auditor |
| Dev tools | [quick-gate-python](https://github.com/hermes-labs-ai/quick-gate-python) | Python quality gate |
| Dev tools | [quick-gate-js](https://github.com/hermes-labs-ai/quick-gate-js) | JS/TS quality gate |
| Dev tools | [csv-quality-gate](https://github.com/hermes-labs-ai/csv-quality-gate) | CSV preflight validation |
