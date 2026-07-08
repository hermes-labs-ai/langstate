"""
langstate.bench_adapters — production adapter sweep on a 100-message corpus.

Runs the three production adapters (local qwen3:14b, OpenAI gpt-4o-mini,
Anthropic claude-opus-4-7) against the same 100-message conversation and
records, per adapter:

    - compression ratio (token-proxy, 4 chars per token)
    - wall latency
    - fact-survival rate: fraction of pre-baked ground-truth facts that
      appear in the scaffold summary (a simple lexical proxy for state
      preservation, not a formal information-theoretic measure)

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
    ("founder_name",       "Dana"),
    ("project_name",       "NoteFlow"),
    ("approach",           "keyword clustering"),
    ("measurement",        "grouping accuracy"),
    ("key_result",         "78%"),
    ("compression_ratio",  "50%"),
    ("first_product",      "notes(text)"),
    ("local_model",        "qwen3"),
    ("milestone_event",    "v0.1 tag"),
    ("test_set_size",      "50 files"),
    ("related_project",    "TagSort"),
    ("benchmark_script",   "benchmark script"),
    ("related_competitor", "TagSort"),
    ("secondary_audience", "students"),
    ("tam_angle",          "developers"),
    ("budget",             "zero budget"),
    ("follow_on_feature",  "GUI wrapper"),
    ("pricing_model",      "free/open source"),
    ("distribution",       "open source"),
    ("tool_name",          "NoteFlow CLI"),
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
        ("My name is Dana and I'm building a small side project called NoteFlow.",
         "Good to meet you, Dana. NoteFlow — what's the core feature?"),
        ("The idea is automatic note grouping by topic. "
         "I measured grouping accuracy on a labeled test set and got 78%.",
         "78% is a solid starting point. How did you measure it?"),
        ("Across 50 test files I clocked roughly 50% token reduction with grouping preserved.",
         "50% reduction with grouping preserved is a reasonable tradeoff. What ships first?"),
        ("The first product is notes(text) — a small CLI that any editor can call. "
         "It runs on a local qwen3 model so the MVP has zero per-call cost.",
         "Clean wedge. Who's it for?"),
        ("Developers keeping plain-text scratch notes. Students are the secondary audience.",
         "Both value fast capture over polish. Timeline?"),
        ("Short write-up once accuracy is good enough, no hard deadline.",
         "Reasonable. What's the current comparison landscape look like?"),
        ("Test set: 50 note files, one small labeled sample. TagSort is a similar tool using tags.",
         "Worth a short comparison. Any other close neighbours?"),
        ("Not that I've found yet — most similar tools use full embeddings, which cost more to run.",
         "Worth calling that tradeoff out explicitly in the write-up."),
        ("The rough plan is CLI, then benchmark script, then decide on a GUI wrapper.",
         "Sequence is right — CLI and benchmark first, GUI later. Don't split focus."),
        ("Distribution: open source the CLI, no revenue plan for now. GUI is a possible follow-on.",
         "Sequence is right — ship the CLI, gather feedback, decide on the GUI after."),
    ]
    for u, a in seed_turns:
        msgs.extend(_make_turn(u, a))

    # Fill to 100 messages with mid-salience noise that refers back to project state.
    filler = [
        ("How do I think about versioning?", "Semantic versioning, tag v0.1 once tests are green."),
        ("Which users should I get feedback from first?", "A few developers who already keep plain-text notes. Concrete use case."),
        ("Should I write more tests before adding features?", "Tests first. Lock in current behavior before you change it."),
        ("What's the right blog cadence?", "One short post once the benchmark numbers are stable."),
        ("Do I open up a Discord?", "Not yet. GitHub issues are enough while the userbase is small."),
        ("How do I get more users?", "Share the benchmark numbers and the write-up. Let the results speak."),
        ("Should I file anything formal before sharing this?", "No, this is a small open-source side project — just ship it."),
        ("What's the profile for a second contributor?", "Someone comfortable with small Python CLIs who enjoys reading benchmark output."),
        ("How should I track feedback?", "A simple GitHub issues board is enough at this size."),
        ("When should I consider a GUI?", "After the CLI is stable and the benchmark numbers hold up."),
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
