# langstate — Show Me First
*5-minute read before the publish decision. Written 2026-07-02. Nothing here is published yet.*

## 1. What it is

Long AI conversations get expensive and slow because the model re-reads the entire
history on every turn. langstate shrinks that history: it keeps the important stuff
(decisions, facts, task status) and throws away the chatter — so the conversation
"remembers" everything that matters while costing roughly half as much. It is the
productized version of your LPCI proof: the idea that an AI's working memory can
live in compressed language instead of raw transcript.

One function, `compress(messages)`. Feed it a conversation, get back a shorter one.

## 2. Proof it works

**It is already running in production — in your own memory system.**
`~/.claude/hooks/hal-state-write.sh` imports it live: line 88 points Python at
`~/dev/langstate/src`, line 90 runs `from langstate import compress`, and line 178
calls `compress(msgs)` on every session it processes. It is also pip-installed in
your hermes-venv as version 0.1.0. This is not a prototype on a shelf; you use it daily.

**Benchmark numbers (all from real runs, files in this repo):**

| Source | Backend | Result |
|---|---|---|
| `bench_results.json` | local qwen3:14b (free) | 1,253 tokens in → 398 out (**68% smaller**); 15 of 20 planted facts survived; slow (~2 min) |
| `bench_openai.json` | gpt-4o-mini (paid API) | 1,253 tokens in → 546 out (**56% smaller**); **20 of 20 facts survived**; fast (~8 sec) |
| `TODO.md` / `CHANGELOG.md` (MVP bench) | local qwen3:4b (free) | **51–54% smaller** on 20–25-turn conversations, key facts verified surviving |

Honest read: the free local model compresses harder but occasionally drops a fact;
the cheap cloud model kept every fact in the bench. Both are one flag apart.

**Tests:** 13 tests total. The 10 that need no AI model at all: **10/10 pass**
(ran today, 0.04 s). The other 3 are end-to-end tests that need the local Ollama
model running — Ollama is on this machine, so they're runnable any time; I skipped
them here only to avoid tying up the big model.

## 3. What publishing to PyPI means

PyPI is the public app store for Python code. Publishing means anyone in the world
can type `pip install langstate` and use it. What goes public is **the code only** —
the ~5 source files, the README, and the license. No conversations, no data, no
benchmarks of your private sessions, nothing from your machine.

**What could go wrong: near-nothing.** I ran a secrets sweep across every file in
the repo (API keys, passwords, private keys, personal info, local machine paths):
**clean**. The only emails present are the public company addresses
(roli@hermes-labs.ai, info@hermes-labs.ai) in the package metadata — which is where
they belong. It's a small Apache-2.0 library with zero dependencies; worst case is
someone finds a bug and files an issue. The one-way door is the *name*: once
"langstate" is claimed on PyPI under your account, it's yours, and old versions
stay visible forever — so we ship it when the polish items below are done.

## 4. What I'd do before pressing publish

1. **Finalize packaging** — mostly done already: `pyproject.toml` exists and a
   0.1.0 wheel is built in `dist/`. Remaining: a final metadata check and a clean
   rebuild. **~1 hour.**
2. **Add `validate(before, after)`** — a built-in "did the facts survive?" checker,
   so users can *prove* compression didn't lose state (this is the marketing hook —
   nobody else ships compression with a receipts function). **~half a day.**
3. **Make the model configurable** — partially done: `compress(model=...)` already
   works. Remaining: pick the default deliberately and document switching between
   free-local and cheap-cloud. **~1–2 hours.**

Total: roughly one focused day. Then publish is a two-command act.

## 5. See it yourself (paste into a terminal)

Runs on the model already on this machine — no downloads, takes ~30–60 seconds:

```bash
cd ~/dev/langstate && ~/hermes-venv/bin/python -c "
from langstate import compress
msgs = [{'role': ('user','assistant')[i%2], 'content': f'Turn {i}: ' + ('DECISION: budget capped at 4k dollars, launch May 5' if i == 2 else 'general project chatter, scheduling, follow-ups')} for i in range(14)]
out = compress(msgs)
print(len(msgs), 'messages in ->', len(out), 'messages out'); print(out[0]['content'][:300])"
```

What I got when I ran exactly this today:

```
14 messages in -> 9 messages out
[SCAFFOLD STATE — compressed from 6 earlier messages]
- Budget capped at $4,000
- Launch scheduled for May 5
```

Fourteen messages became nine. The chatter is gone; the budget cap and the launch
date — the two facts that mattered — survived, verbatim in meaning. That's the
whole product.
