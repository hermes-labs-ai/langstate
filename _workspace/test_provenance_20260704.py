"""Provenance direction of langstate.validate — Roli's generalization, proven live.

Survival  = validate(before, after): facts extracted from SOURCE must appear in OUTPUT
            (catches silent loss).
Provenance = validate(after, before): facts extracted from OUTPUT must appear in SOURCE
            (catches fabrication/hallucination). Same machinery, arguments flipped.

Demo boundary: the compressed morning brief from test_log_compression_20260704.py.
Provenance needs no LLM call — extraction + substring check are deterministic.
"""
import sys, re
sys.path.insert(0, "/Users/rbr_lpci/dev/langstate/src")
from langstate import compress, validate

text = open("/Users/rbr_lpci/dev/forever-memory/HANDOFF.md").read()
start = text.index("## OPUS-NIGHT-MANAGER morning brief")
end = text.index("# SYSTEM-INTEGRATION worker")
brief = text[start:end]
paras = [p for p in re.split(r"\n(?=- |### |## |\*\*)", brief) if p.strip()]
messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": p}
            for i, p in enumerate(paras)]

out = compress(messages, preserve_recent=2)

surv = validate(messages, out).as_dict()
prov = validate(out, messages).as_dict()

print("SURVIVAL  (did the output keep the source's facts?)")
print(f"  {len(surv['survived'])}/{surv['total']} kept ({surv['survival_rate']:.0%})  ok={surv['ok']}")
print("PROVENANCE (does every fact in the output exist in the source?)")
print(f"  {len(prov['survived'])}/{prov['total']} grounded ({prov['survival_rate']:.0%})  ok={prov['ok']}")
fab = prov["dropped"]
print(f"  facts in output with NO source support (fabrication candidates): {len(fab)}")
for f in fab[:8]:
    print("   ⚠", f[:110])
