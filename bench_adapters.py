"""
langstate.bench_adapters — production adapter sweep on a 100-message corpus.

Runs the three production adapters (local qwen3:14b, OpenAI gpt-4o-mini,
Anthropic claude-opus-4-7) against the same 100-message conversation and
records, per adapter:

    - compression ratio (token-proxy, 4 chars per token)
    - wall latency
    - fact-survival rate: fraction of pre-baked ground-truth facts that
      appear in the scaffold summary (honest proxy for state preservation
      in lieu of a full transfer-entropy pipeline)

Unreachable adapters are skipped with a reason; the bench still completes.
Output is both a human-readable table on stdout and a JSON artifact at
``bench_results.json`` in the current directory.

Usage:
    python3 bench_adapters.py                         # run all adapters
    python3 bench_adapters.py --only local            # a single adapter
    python3 bench_adapters.py --out /tmp/bench.json   # custom output path
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from adapters import REGISTRY, AdapterUnavailable, build  # noqa: E402
from compress import _count_messages_tokens, compress  # noqa: E402

# ---------------------------------------------------------------------------
# 100-message synthetic corpus with pre-declared ground-truth facts.
# Every fact below is injected into a user turn verbatim. The scaffold
# summary should still contain recognizable traces of each fact after
# compression; "fact-survival" counts how many do.
# ---------------------------------------------------------------------------

GROUND_TRUTH = [
    ("founder_name",       "Roli"),
    ("company_name",       "Hermes Labs"),
    ("thesis",             "LPCI"),
    ("measurement",        "transfer entropy"),
    ("key_result",         "TE"),
    ("compression_ratio",  "2.5x"),
    ("first_product",      "compress(messages)"),
    ("local_model",        "qwen3"),
    ("deadline_event",     "NeurIPS"),
    ("corpus_size",        "530MB"),
    ("arxiv_papers",       "155"),
    ("benchmarks",         "718"),
    ("related_competitor", "Millidge"),
    ("universal_result",   "Schuurmans"),
    ("tam_angle",          "compliance"),
    ("seed_ask",           "$2M"),
    ("follow_on_paper",    "multi-agent"),
    ("pricing_model",      "hosted API"),
    ("distribution",       "open source"),
    ("tool_name",          "ScaffoldGit"),
]


def _make_turn(user: str, assistant: str) -> list[dict]:
    return [
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]


def build_corpus_100() -> list[dict]:
    """Return a 100-message (1 system + 99 user/assistant) corpus.

    The first turns inject ground-truth facts in dense, realistic prose;
    subsequent turns are lower-salience noise that tests whether the
    compressor preserves the early high-salience facts under pressure.
    """
    msgs: list[dict] = [{"role": "system", "content": "You are a helpful research strategist."}]

    seed_turns = [
        ("My name is Roli and I'm building a company called Hermes Labs focused on AI audit.",
         "Good to meet you, Roli. Hermes Labs — what's the product wedge?"),
        ("Our thesis is LPCI: stateless LLMs hold state via language scaffold. "
         "We measured transfer entropy from scaffold to model output and got TE approximately zero.",
         "TE ≈ 0 is a strong claim. How did you measure?"),
        ("Across 500 inference calls we clocked a 2.5x compression ratio with Markov sufficiency preserved.",
         "2.5x with Markov sufficiency is defensible. What ships first?"),
        ("The first product is compress(messages) — a middleware that any agent framework can call. "
         "We run it on a local qwen3 model so the MVP has zero per-call cost.",
         "Clean wedge. Who pays for it?"),
        ("Agent framework builders in production. Enterprise compliance is the bigger angle.",
         "Compliance reads well against the EU AI Act. Timeline?"),
        ("Preprint before NeurIPS 2026 submission in May. Priority date matters.",
         "Tight. What's the related-work landscape look like?"),
        ("Corpus: 530MB, 155 arxiv papers, 718 benchmarks. TE appears zero times in 470MB of related work.",
         "Uncontested novelty. Closest neighbours?"),
        ("Schuurmans proved autoregressive chaining equals universal computation. Millidge made the qualitative claim in 2023.",
         "Frame as Millidge's empirical proof. Lead with the measurement."),
        ("The VC pitch bundles ScaffoldGit + Driftwatch as Agent Observability. $2M seed ask.",
         "Version control + monitoring, LPCI as correctness theory. Strong narrative."),
        ("Distribution: open source the library, revenue from hosted API. Multi-agent paper is the follow-on.",
         "Sequence is right — single-agent first, multi-agent next. Don't split focus."),
    ]
    for u, a in seed_turns:
        msgs.extend(_make_turn(u, a))

    # Fill to 100 messages with mid-salience noise that refers back to project state.
    filler = [
        ("How do I think about pricing tiers?", "Metered on compressed tokens. $X per million. Enterprise flat."),
        ("Which design partners should I target first?", "Fintech compliance teams and legal tech vendors. Concrete pain."),
        ("Should I hire a researcher before a PM?", "Researcher. The wedge is still academic."),
        ("What's the right blog cadence?", "One technical post per week through launch."),
        ("Do I open up a Discord?", "Not yet. GitHub issues are enough while the userbase is small."),
        ("How do I defend against copycats?", "The proof is the moat. Citations and early customer logos."),
        ("Should I file a provisional patent?", "No. Open science plays better here and patents slow you down."),
        ("What's the hiring profile for the second engineer?", "Infra-leaning Python generalist. Must read papers."),
        ("How do I structure the board?", "One investor seat, one independent, one you. Keep it boring."),
        ("When should I raise the A?", "Twelve months after seed or at $100k MRR, whichever is first."),
    ]
    while len(msgs) < 100:
        for u, a in filler:
            msgs.extend(_make_turn(u, a))
            if len(msgs) >= 100:
                break
    return msgs[:100]


def fact_survival(scaffold_text: str) -> tuple[int, int, list[str]]:
    """Count how many ground-truth facts appear (case-insensitive substring)
    in the scaffold summary. Returns (hits, total, missing_keys)."""
    text = scaffold_text.lower()
    hits = 0
    missing: list[str] = []
    for key, needle in GROUND_TRUTH:
        if needle.lower() in text:
            hits += 1
        else:
            missing.append(key)
    return hits, len(GROUND_TRUTH), missing


def extract_scaffold(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "system" and "SCAFFOLD STATE" in m.get("content", ""):
            return m["content"]
    return ""


def run_one(name: str, corpus: list[dict]) -> dict:
    """Run one adapter against the corpus and return a row dict."""
    try:
        summarizer = build(name)
    except AdapterUnavailable as e:
        return {"adapter": name, "available": False, "reason": str(e)}

    t0 = time.time()
    try:
        compressed = compress(corpus, summarizer=summarizer)
    except AdapterUnavailable as e:
        return {"adapter": name, "available": False, "reason": f"runtime: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"adapter": name, "available": False, "reason": f"{type(e).__name__}: {e}"}
    latency_ms = int((time.time() - t0) * 1000)

    input_tokens = _count_messages_tokens(corpus)
    output_tokens = _count_messages_tokens(compressed)
    ratio = 1.0 - (output_tokens / input_tokens) if input_tokens else 0.0
    scaffold = extract_scaffold(compressed)
    hits, total, missing = fact_survival(scaffold)

    return {
        "adapter":        name,
        "label":          REGISTRY[name][0],
        "available":      True,
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "compression":    round(ratio, 3),
        "latency_ms":     latency_ms,
        "fact_hits":      hits,
        "fact_total":     total,
        "fact_survival":  round(hits / total, 3) if total else 0.0,
        "missing_facts":  missing,
        "scaffold_chars": len(scaffold),
    }


def print_table(rows: list[dict]) -> None:
    print("=" * 88)
    print(f"langstate.bench_adapters — 100-message corpus, {len(GROUND_TRUTH)} ground-truth facts")
    print("=" * 88)
    header = f"{'adapter':<10} {'label':<26} {'compr':>7} {'survival':>9} {'lat(s)':>8} {'status'}"
    print(header)
    print("-" * len(header))
    for r in rows:
        if not r.get("available"):
            print(f"{r['adapter']:<10} {'—':<26} {'—':>7} {'—':>9} {'—':>8} SKIP: {r['reason'][:40]}")
            continue
        print(
            f"{r['adapter']:<10} {r['label']:<26} "
            f"{r['compression']:>6.1%} {r['fact_survival']:>8.1%} "
            f"{r['latency_ms']/1000:>8.1f} OK"
        )
    print("=" * 88)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(REGISTRY), help="run only one adapter")
    ap.add_argument("--out",  default=str(HERE / "bench_results.json"))
    args = ap.parse_args()

    corpus = build_corpus_100()
    if len(corpus) != 100:
        print(f"WARN: corpus size {len(corpus)} != 100")
    names = [args.only] if args.only else list(REGISTRY)
    rows = [run_one(n, corpus) for n in names]

    print_table(rows)

    Path(args.out).write_text(json.dumps({
        "corpus_size": len(corpus),
        "ground_truth_facts": len(GROUND_TRUTH),
        "results": rows,
    }, indent=2))
    print(f"\nWrote {args.out}")
    ok = any(r.get("available") for r in rows)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
