# langstate — REVERT-LEDGER (Opus night manager, 2026-07-03→04)

Every change below is local-only (no push, no publish). One-line restore per entry.
Repo has a dormant `.hermes-seal.yaml` — seal is PARKED/not-enforced; edits here intentionally
leave the seal stale (do NOT re-sign; `grant` is root-only, MAXIM 15).

## P1 — langstate publish-ready — DONE (local commit `e3455d6`, NOT pushed, NOT published)

Whole-batch restore: `git revert e3455d6`  (or per-file: `git checkout e3455d6^ -- <path>`)

- CHANGE: new `validate(before, after)` + `Receipt` + `extract_facts` (zero-dep, deterministic facts-survived receipt) | FILE: src/langstate/validate.py (new) | RESTORE: rm file / revert
- CHANGE: export validate/Receipt/extract_facts + add `__version__ = "0.1.0"` | FILE: src/langstate/__init__.py | RESTORE: git checkout e3455d6^ -- src/langstate/__init__.py
- CHANGE: 9 new tests for validate (no model) | FILE: tests/test_validate.py (new) | RESTORE: rm file
- CHANGE: unify default model → qwen3:4b (DEFAULT_LOCAL_MODEL + REGISTRY label + docstring); anthropic default claude-opus-4-7 → claude-haiku-4-5-20251001 | FILE: src/langstate/adapters.py | RESTORE: git checkout e3455d6^ -- src/langstate/adapters.py
- CHANGE: registry-assertion test updated to new defaults | FILE: tests/test_adapters.py | RESTORE: git checkout e3455d6^ -- tests/test_adapters.py
- CHANGE: README — model table 14b→4b + opus→haiku; new "Prove the state survived" (validate) + "Choosing a model" (switching docs) sections; swapped example name Roli→Dana; dropped falsifiable "runs in production" line | FILE: README.md | RESTORE: git checkout e3455d6^ -- README.md
- CHANGE: CHANGELOG — expanded v0.1.0 (validate, default unify, adapters) | FILE: CHANGELOG.md | RESTORE: git checkout e3455d6^ -- CHANGELOG.md
- CHANGE: moved bench module OUT of shipped package (was importable-but-broken + bundled internal probe strings); fixed its imports to langstate.* | FILE: src/langstate/te_check.py → bench/te_check.py | RESTORE: git mv bench/te_check.py src/langstate/te_check.py
- CHANGE: clean rebuild of wheel + sdist (0.1.0), twine-checked; verified te_check + private corpus NOT in either artifact | FILE: dist/langstate-0.1.0-py3-none-any.whl, dist/langstate-0.1.0.tar.gz | RESTORE: `python -m build` regenerates
- CHANGE: PUBLISH-RUNBOOK.md (Roli's two commands for tomorrow) | FILE: PUBLISH-RUNBOOK.md (new) | RESTORE: rm file

NOTE: `.hermes-seal.yaml` seal is now stale after this commit — EXPECTED (seal is parked/not-enforced; do NOT re-sign, `grant` is root-only, MAXIM 15).
DONE-test evidence: fresh venv (py3.14) `pip install` the wheel → import + validate work, te_check excluded; test suite 19 passed / 3 Ollama-gated skipped; twine check PASSED (wheel + sdist).
