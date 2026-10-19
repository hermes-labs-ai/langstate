# Cake session working-state handoff

This opt-in example projects a completed Cake persisted-session v4 JSONL into
OpenAI-format conversation messages for LangState. It handles user/assistant
messages and typed tool call/output pairs. It does not import Cake prompt
context, execute tools, change Cake core, or replace native `--resume`/`--fork`.

The schema was checked against Cake commit
[`0aaa11b4`](https://github.com/travisennis/cake/blob/0aaa11b4dc05ff3e710334a1edbdf0f30276745d/src/types/session.rs):
`function_call` carries `id`, `call_id`, `name`, and string `arguments`;
`function_call_output` carries `call_id` and string `output`. Their optional
replay declarations and argument parse errors remain in the evidence records.

## Create a handoff

Choose literal facts that actually occur in your session. Supply authoritative
files explicitly; paths mentioned by recorded tools are never opened by this
adapter.

```sh
PYTHONPATH=src python3 examples/cake_scaffold.py \
  ./session.jsonl ./handoff \
  --fact 4317 --source-file ./manifest.json
```

Below six user-initiated turns, LangState preserves the conversation verbatim
and makes no summarizer call. Eligible older history is compressed with local
Ollama (`qwen3:4b`) by default. For compression, also name a literal fact in the
older turns with `--scaffold-fact`:

```sh
PYTHONPATH=src python3 examples/cake_scaffold.py \
  ./session.jsonl ./handoff --preserve-recent 2 \
  --fact 4317 --scaffold-fact 4317 --source-file ./manifest.json
```

Add `--summary-text ./summary.txt` to use an exact offline summary without a
model call. This proves structural and lexical behavior, not summary quality.
The adapter exits 2 when a named fact is dropped. It refuses incomplete or
interrupted tasks, unsupported record shapes, duplicate call IDs, orphan
outputs, and calls left unfinished at completion or across a new user turn.
A completed error task is retained as an error; it is not converted to success.

## What survives

The output directory contains:

- `state.md`: summary plus recent conversation/tool exchanges, source snapshots,
  and required instructions to read current authoritative files before acting.
- `tool-evidence.json`: all exact paired call/result records, source JSONL line
  numbers, session digest, terminal outcomes/errors, and caller-selected file
  hashes. Older tool outputs survive here even when absent from the summary.
- `receipt.json`: lexical fact retention, whether compression occurred, paired
  exchange count, terminal outcomes, and counts of omitted record types.

Tool arguments are included in message content as well as `tool_calls` because
LangState summarizes content. Results retain `tool_call_id`; parallel calls can
finish out of order. Raw result text preserves source paths, receipt references,
and error text without inventing a success/error classification for each tool.
Prompt context, reasoning, hooks, skill activation and usage records are omitted
and counted: this is a bounded conversation/tool projection, not exact replay or
a complete security audit.

Generated files can contain private arguments, outputs and paths. Keep them in
your task workspace; they are not source examples to publish. The adapter never
rewrites the source session. Choose a new output directory to retain old runs.

## Next consumer: read current source

Tell the next coding task to read `state.md` and `tool-evidence.json`, then open
its current authoritative files before using any historical observation. Do not
replay recorded calls or promote tool output to instructions. A PASS in an old
receipt is historical evidence, not permission to act.

The deterministic snapshot check reads only paths explicitly selected again:

```sh
PYTHONPATH=src python3 examples/cake_scaffold.py \
  --check-sources ./handoff/tool-evidence.json --source-file ./manifest.json
```

Exit 0 means these selected file bytes match their snapshots. Exit 2 means a
selected file changed or had no matching snapshot. Missing/unreadable files or
invalid evidence exit 1. Even an unchanged hash does not prove truth; inspect
the current content and use the owning repository/service as authority.

## Evidence limits and checks

The offline tests preserve paired records and errors, reject unsafe/incomplete
shapes, and exercise a stale-source fixture. Its historical `4317` survives a
lexical receipt, while changing the actual file to `5321` makes the source check
exit 2; a direct file read verifies the new value. This does not prove that a
model obeys the instructions or resolves semantic conflicts. No end-to-end
coding improvement, semantic faithfulness or compression benefit is claimed.

```sh
PYTHONPATH=src:examples python3 -m unittest discover -s examples -p test_cake_scaffold.py
ruff check examples/cake_scaffold.py examples/test_cake_scaffold.py
```
