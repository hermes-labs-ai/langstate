"""Live test of Roli's idea #2: compress operational logging with langstate.
Input: the OPUS-NIGHT-MANAGER morning brief section of HANDOFF.md (real artifact
that future sessions re-read). Measures size reduction + fact survival receipt.
"""
import sys, time, re
sys.path.insert(0, "/Users/rbr_lpci/dev/langstate/src")
from langstate import compress, validate

text = open("/Users/rbr_lpci/dev/forever-memory/HANDOFF.md").read()
start = text.index("## OPUS-NIGHT-MANAGER morning brief")
end = text.index("# SYSTEM-INTEGRATION worker")
brief = text[start:end]

paras = [p for p in re.split(r"\n(?=- |### |## |\*\*)", brief) if p.strip()]
messages = []
for i, p in enumerate(paras):
    messages.append({"role": "user" if i % 2 == 0 else "assistant", "content": p})

before_chars = sum(len(m["content"]) for m in messages)
t0 = time.time()
out = compress(messages, preserve_recent=2)
dt = time.time() - t0
after_chars = sum(len(m["content"]) for m in out)

r = validate(messages, out)
d = r.as_dict()
print(f"input:  {before_chars:,} chars in {len(messages)} msgs")
print(f"output: {after_chars:,} chars in {len(out)} msgs")
print(f"reduction: {1 - after_chars/before_chars:.1%}  wall: {dt:.1f}s (qwen3:4b local, $0)")
print(f"receipt: {d['survived'] and len(d['survived'])}/{d['total']} facts survived "
      f"({d['survival_rate']:.0%})  ok={d['ok']}")
print("--- sample dropped facts (first 5):")
for f in d["dropped"][:5]:
    print("  ✗", f[:110])
