"""langstate.te_check — honest transfer-entropy proxy on the 100-message corpus.

We can't measure continuous transfer entropy against a closed model in the
usual way (no joint-distribution access). So we measure a downstream
*behavioral* TE proxy instead, which is the only defensible proxy when the
model is a black box:

    TE-proxy = 1 - recall(probe | compressed)
                  ---------------------------
                  recall(probe | full_history)

Method (single constant probe model for all conditions to isolate the
compression signal):

    * Probe model: ``qwen3:8b`` on local Ollama (deterministic, temperature 0).
    * Probes: 10 cloze-style questions whose answers appear exactly once in
      the early turns of the corpus.
    * For each adapter ``A`` we form two conversations:
        full_A        = corpus + probe
        compressed_A  = compress(corpus, summarizer=A) + probe
      and score the probe model's answer with case-insensitive substring
      match against the ground-truth needle.
    * Report per-adapter: recall_full, recall_compressed, delta.
      delta ≈ 0 is the empirical TE-proxy-≈-zero claim.

This is an imperfect TE estimator but it is honestly labelled as a
*behavioral* proxy and the math is transparent.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # repo root, where bench_adapters.py lives
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langstate.adapters import REGISTRY, AdapterUnavailable, build  # noqa: E402
from langstate.compress import compress  # noqa: E402
from bench_adapters import build_corpus_100  # noqa: E402


PROBE_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# (question, ground_truth_substring) — answers appear verbatim in the corpus.
PROBES = [
    ("What is the user's first name?", "roli"),
    ("What is the name of the user's company?", "hermes"),
    ("What acronym describes their core thesis?", "lpci"),
    ("What measurement did they report as approximately zero?", "transfer entropy"),
    ("What compression ratio did they measure?", "2.5"),
    ("What is the name of the first product they plan to ship?", "compress"),
    ("What conference submission deadline is driving their timeline?", "neurips"),
    ("How large is the research corpus they built, in MB?", "530"),
    ("Which researcher proved autoregressive chaining equals universal computation?", "schuurmans"),
    ("What is their seed fundraise ask?", "2m"),
]


def _ollama_chat(messages: list[dict], model: str = PROBE_MODEL, timeout: int = 120) -> str:
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 160, "seed": 7},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"probe model unreachable: {e}") from e
    return (result.get("message") or {}).get("content", "").strip()


PROBE_SYSTEM = (
    "Answer from the supplied conversation state only. "
    "Respond with the single fact asked for, no preamble, no hedging. "
    "If the answer is not present, say NOT_PRESENT."
)


def _score(answer: str, needle: str) -> int:
    return int(needle.lower() in answer.lower())


def _run_probes(context_msgs: list[dict]) -> tuple[int, list[dict]]:
    hits = 0
    rows: list[dict] = []
    for q, needle in PROBES:
        convo = [{"role": "system", "content": PROBE_SYSTEM}, *context_msgs,
                 {"role": "user", "content": q}]
        ans = _ollama_chat(convo)
        ok = _score(ans, needle)
        hits += ok
        rows.append({"q": q, "needle": needle, "answer": ans[:200], "hit": ok})
    return hits, rows


def run_adapter(name: str, corpus: list[dict]) -> dict:
    """Compare recall under full vs compressed context for one adapter."""
    try:
        summarizer = build(name)
    except AdapterUnavailable as e:
        return {"adapter": name, "available": False, "reason": str(e)}

    t0 = time.time()
    try:
        compressed = compress(corpus, summarizer=summarizer)
    except Exception as e:  # noqa: BLE001
        return {"adapter": name, "available": False, "reason": f"compress: {e}"}
    compress_seconds = time.time() - t0

    # shared full-context recall only needs to run once per bench; we still
    # do it per adapter so every row is a standalone comparison.
    full_hits, full_rows = _run_probes(corpus)
    comp_hits, comp_rows = _run_probes(compressed)

    n = len(PROBES)
    recall_full = full_hits / n
    recall_comp = comp_hits / n
    delta = recall_full - recall_comp
    te_proxy = max(delta, 0.0)

    return {
        "adapter":           name,
        "label":             REGISTRY[name][0],
        "available":         True,
        "n_probes":          n,
        "recall_full":       round(recall_full, 3),
        "recall_compressed": round(recall_comp, 3),
        "delta":             round(delta, 3),
        "te_proxy":          round(te_proxy, 3),
        "compress_seconds":  round(compress_seconds, 2),
        "rows_full":         full_rows,
        "rows_compressed":   comp_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(REGISTRY))
    ap.add_argument("--out", default=str(HERE / "te_results.json"))
    args = ap.parse_args()

    corpus = build_corpus_100()
    names = [args.only] if args.only else list(REGISTRY)
    rows = [run_adapter(n, corpus) for n in names]

    print("=" * 78)
    print(f"langstate.te_check — n={len(PROBES)} probes, probe_model={PROBE_MODEL}")
    print("=" * 78)
    print(f"{'adapter':<10} {'label':<22} {'full':>6} {'comp':>6} {'delta':>7} {'TE~':>6}")
    print("-" * 78)
    for r in rows:
        if not r.get("available"):
            print(f"{r['adapter']:<10} {'—':<22} {'—':>6} {'—':>6} {'—':>7} {'—':>6} SKIP: {r['reason'][:30]}")
            continue
        print(
            f"{r['adapter']:<10} {r['label']:<22} "
            f"{r['recall_full']:>6.1%} {r['recall_compressed']:>6.1%} "
            f"{r['delta']:>+7.1%} {r['te_proxy']:>6.3f}"
        )
    print("=" * 78)

    Path(args.out).write_text(json.dumps({
        "probe_model": PROBE_MODEL,
        "n_probes": len(PROBES),
        "corpus_size": len(corpus),
        "results": rows,
    }, indent=2))
    print(f"Wrote {args.out}")
    return 0 if any(r.get("available") for r in rows) else 2


if __name__ == "__main__":
    sys.exit(main())
