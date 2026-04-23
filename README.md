# langstate

Scaffold-aware context compression for OpenAI-format messages. `compress(messages)` preserves all conversational state — facts, decisions, task status, user preferences — while reducing tokens by 50-54%.

Backed by the LPCI thesis: stateless LLMs hold state via language scaffold with transfer entropy approximately zero (Markov property). This is the productization of that proof.

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
| `local` (default) | qwen3:14b via Ollama | zero | none |
| `openai` | gpt-4o-mini | API | `OPENAI_API_KEY` |
| `anthropic` | claude-opus-4-7 | API | `ANTHROPIC_API_KEY` |

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
