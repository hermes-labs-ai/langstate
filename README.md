# langstate

Scaffold-aware context compression for OpenAI-format messages. `compress(messages)` preserves all conversational state — facts, decisions, task status, user preferences — while reducing tokens by 50-54%.

Built on the LPCI approach: stateless models hold working state through the language scaffold in their context. langstate productizes that idea — it compresses older history into a state-preserving `[SCAFFOLD STATE]` summary and ships a receipt proving which facts survived.

## What it does

```python
from langstate import compress

compressed = compress(messages)
# Drop-in replacement: same OpenAI format, fewer tokens, state preserved
response = client.chat.completions.create(messages=compressed, model="gpt-4o")
```

The output is a valid OpenAI-format messages list:
- System prompts kept verbatim
- Last 4 turn-pairs kept verbatim
- Older turns compressed into a `[SCAFFOLD STATE]` system message via local or cloud model

## Prove the state survived — the receipt

Compression that silently drops a fact is worse than no compression. `validate`
returns a receipt — deterministic, no model call, runs in CI:

```python
from langstate import compress, validate

compressed = compress(messages)

# Check the specific facts you care about:
receipt = validate(messages, compressed,
                   facts=["$4,000 budget", "launch May 5", "Dana"])

print(receipt.summary())   # "3/3 facts survived (100%) · 52% smaller"
print(receipt.dropped)     # [] — nothing lost
assert receipt.ok          # gate your pipeline on it

# Or let it auto-extract salient facts (numbers, money, acronyms, names):
receipt = validate(messages, compressed)
```

The check is intentionally *lexical* — a fact counts as survived only if it is
present verbatim in the compressed messages. That under-counts (it can't credit
a paraphrase) rather than over-claims — the honest direction for a receipt.
`receipt.as_dict()` gives a JSON-friendly record to log.

## Install

```bash
# From GitHub (PyPI coming soon):
pip install git+https://github.com/hermes-labs-ai/langstate.git
```

Requirements: Python 3.10+, no heavy dependencies (stdlib only). For local summarization, run [Ollama](https://ollama.ai) locally:

```bash
ollama pull qwen3:4b
```

## Adapters

langstate ships three built-in summarizer backends:

| Adapter | Model | Cost | Key |
|---|---|---|---|
| `local` (default) | qwen3:4b via Ollama | zero | none |
| `openai` | gpt-4o-mini | API | `OPENAI_API_KEY` |
| `anthropic` | claude-haiku-4-5 | API | `ANTHROPIC_API_KEY` |

```python
from langstate import compress
from langstate.adapters import build

# Local Ollama (default, zero cost)
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

**The default is local `qwen3:4b` via Ollama** — chosen deliberately: no API key,
zero cost, and quick to pull. It compresses hard and fast; on smaller models a
fact or two can slip, which is exactly what `validate` is for — measure it,
don't assume it.

Pick by what you're optimizing:

| Want | Use | Trade-off |
|---|---|---|
| Zero cost, no key, offline | `local` — qwen3:4b (default) | fastest setup; verify fidelity with `validate` |
| Highest fidelity, cheap | `openai` — gpt-4o-mini | a few cents; kept every planted fact in our bench |
| Anthropic stack | `anthropic` — claude-haiku-4-5 | cheap tier; needs `ANTHROPIC_API_KEY` |
| Full control | your own `summarizer=` | any `(prompt: str) -> str` callable |

Switching is one argument:

```python
compress(messages)                              # local qwen3:4b (default)
compress(messages, model="qwen3:14b")           # bigger local model, slower, higher fidelity
compress(messages, summarizer=build("openai"))  # cloud, highest fidelity
```

If fidelity matters more than cost, run `validate` on a sample of your traffic
and move up a tier until the receipt is green.

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
| Static audit | [scaffold-lint](https://github.com/hermes-labs-ai/scaffold-lint) | Scaffold budget + technique stacking |
| Static audit | [intent-verify](https://github.com/hermes-labs-ai/intent-verify) | Spec-drift checks |
| Runtime observability | [little-canary](https://github.com/hermes-labs-ai/little-canary) | Prompt injection detection |
| Runtime observability | [suy-sideguy](https://github.com/hermes-labs-ai/suy-sideguy) | Runtime policy guard |
| Runtime observability | [colony-probe](https://github.com/hermes-labs-ai/colony-probe) | Prompt confidentiality audit |
| Regression & scoring | [hermes-jailbench](https://github.com/hermes-labs-ai/hermes-jailbench) | Jailbreak regression benchmark |
| Regression & scoring | [agent-convergence-scorer](https://github.com/hermes-labs-ai/agent-convergence-scorer) | N-agent output consistency |
| Supporting infra | [claude-router](https://github.com/hermes-labs-ai/claude-router) | Model-tier + scaffold router |
| Supporting infra | [quickthink](https://github.com/hermes-labs-ai/quickthink) | Compressed planning scaffold for local LLMs |
| Supporting infra | [langstate](https://github.com/hermes-labs-ai/langstate) | Scaffold-aware context compression |
| Supporting infra | [agent-gorgon](https://github.com/hermes-labs-ai/agent-gorgon) | Tool-fabrication defense for Claude Code |
| Supporting infra | [zer0dex](https://github.com/hermes-labs-ai/zer0dex) | Dual-layer agent memory |
| Supporting infra | [forgetted](https://github.com/hermes-labs-ai/forgetted) | Mid-conversation incognito |
| Dev tools | [repo-audit](https://github.com/hermes-labs-ai/repo-audit) | Launch-readiness auditor |
| Dev tools | [quick-gate-python](https://github.com/hermes-labs-ai/quick-gate-python) | Python quality gate |
| Dev tools | [quick-gate-js](https://github.com/hermes-labs-ai/quick-gate-js) | JS/TS quality gate |
| Dev tools | [csv-quality-gate](https://github.com/hermes-labs-ai/csv-quality-gate) | CSV preflight validation |
