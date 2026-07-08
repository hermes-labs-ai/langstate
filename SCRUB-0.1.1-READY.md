# langstate 0.1.1 — SCRUB STAGED, verified clean, NOT published

Staged 2026-07-08. Local-only. Nothing pushed, nothing published, nothing yanked.

## Why this exists

langstate 0.1.0 is live on PyPI. Its published sdist contained (confirmed by
extracting the actual PyPI tarball):
- `tests/test_compress.py` and `src/langstate/te_check.py` — both meant to be
  internal-only, both shipped by mistake in 0.1.0.
- A fake-dialogue test fixture in `test_compress.py` that embedded real
  internal strategy: the "$2M seed / ScaffoldGit + Driftwatch / Agent
  Observability" VC pitch, NeurIPS-2026 priority timing + "window closing",
  the 530MB research-corpus + competitor analysis (Schuurmans/Millidge), and
  the retracted TE≈0 claim.
- `te_check.py` — a "transfer-entropy proxy" benchmark whose entire premise is
  the retracted TE≈0 / Markov-sufficiency claim, plus probe questions that
  re-embed the same private facts (roli/hermes/lpci/neurips/530/2m).
- README/pyproject language crediting the TE≈0 claim (this had already been
  corrected in a prior session pass — confirmed clean below).

## What was scrubbed this pass

- `tests/test_compress.py` (canonical, pytest-discovered) — replaced the VC-pitch
  dialogue fixture with a fully generic "Dana / NoteFlow note-taking app"
  dialogue. Same shape (25 turn-pairs, same turn-count tests), zero real
  content.
- `test_compress.py` (root-level legacy duplicate, still git-tracked) — same
  fixture replaced for consistency; this file isn't part of the shipped
  package (pruned) but was still a plaintext leak in the repo.
- `bench_adapters.py` — `GROUND_TRUTH` list and `build_corpus_100()` seed/filler
  turns rewritten to the same generic Dana/NoteFlow scenario (this was the
  actual source of the VC-pitch corpus that `te_check.py` benchmarked against).
  Docstring's "in lieu of a full transfer-entropy pipeline" phrase also reworded.
- `te_check.py` (root) and `bench/te_check.py` — retracted. Whole premise was
  the retracted TE≈0 claim, so both are now stub modules that `raise
  ImportError` on import with a pointer to CHANGELOG.md v0.1.1, instead of
  computing a "TE-proxy". No PROBES list, no private facts, no functional
  benchmark left.
- `tests/test_validate.py` — minor hygiene: three tests used "$2M"/"TE"/"530MB
  with 155 papers" as arbitrary example fact-tokens (not a strategy leak, but
  the literal digits matched real internal numbers). Swapped to fully generic
  placeholders ("$2,000 budget", "pending", "Kite Labs", "12MB with 40 files").
- `src/langstate/__init__.py` — `__version__` bumped `0.1.0` → `0.1.1` (matches
  `pyproject.toml`, which a prior session had already bumped).
- README.md, llms.txt, pyproject.toml, PKG-INFO — checked, already clean (no
  TE/Markov/750x claims; a prior session pass had already corrected these and
  CHANGELOG.md v0.1.1 documents it). No changes needed here.
- `MANIFEST.in` (pre-existing from a prior pass) already `prune`s `tests/`,
  `bench/`, `_workspace/` and `global-exclude`s `te_check.py` from the sdist —
  this was already working correctly (verified: the *unscrubbed* 0.1.1 sdist
  built before this pass, dated Jul 5, already did NOT contain the leak files).
  This pass's fixture scrub is defense-in-depth for the repo itself, not a fix
  to the packaging boundary.

## Verification

**Framing-lint** (`~/ai-infra/hooks/external-framing-lint.sh`) — run on every
touched file: `README.md`, `pyproject.toml`, `llms.txt`, `tests/test_compress.py`,
`test_compress.py`, `bench_adapters.py`, `te_check.py`, `bench/te_check.py`,
`tests/test_validate.py`. **All exit 0.** (The first draft of the `te_check.py`
retraction stub tripped the banned-phrase regex on its own explanatory
"TE≈0"/"transfer entropy ... 0" text — redrafted to describe the retraction
without reproducing the banned digit-adjacent patterns; second draft passes.)

**Test suite**: `python3 -m pytest tests/ -v` (Ollama reachable, `qwen3:4b`
loaded) — **22 passed, 0 failed** (292s first run caught one assertion typo
from the fixture swap — `NoteFlow` is a single camelCase word the `extract_facts`
proper-noun regex doesn't match; fixed to a two-word `Kite Labs` example; second
run: **22 passed in 129.70s, 0 failed**).

**Sdist build + grep**: `python3 -m build --sdist` (also built the wheel),
`twine check` PASSED on both. Extracted the built tarball and grepped for every
leak marker (`transfer entropy`, `TE approx`, `TE≈0`, `neurips`, `scaffoldgit`,
`driftwatch`, `design partner`, `window closing`, `530MB`, `750x`/`745x`/`851x`,
`agent observability`, `$2M`, `seed ask`/`seed fundraise`, `schuurmans`,
`millidge`) — **zero matches**. Confirmed `SOURCES.txt` — the sdist ships only
`LICENSE`, `MANIFEST.in`, `README.md`, `pyproject.toml`, and
`src/langstate/{__init__,adapters,compress,validate}.py`. `TODO.md` and
`AGENTS.md` (which still reference the retracted TE claim / 530MB corpus
internally) are confirmed NOT packaged — they're internal dev docs in a
private repo, out of scope for this pass, and don't reach PyPI.

Built artifacts are in `~/dev/langstate/dist/`:
`langstate-0.1.1.tar.gz` (17,582 bytes), `langstate-0.1.1-py3-none-any.whl`
(15,938 bytes) — both built fresh from the scrubbed source (2026-07-08 18:33).

## What's NOT done (needs Roli's armed word)

Nothing has been committed, pushed, published, or yanked. Working tree has
uncommitted changes (`git status` on `~/dev/langstate` shows the scrubbed
files as modified/untracked).

## Publish + yank command sequence (for when Roli arms it)

```bash
cd ~/dev/langstate

# 1. Commit the scrub locally (reversible, not yet requested — do this first if approved)
git add -A
git commit -m "fix: scrub internal strategy + retracted TE claim from tests/bench, bump to 0.1.1"

# 2. Publish 0.1.1 to PyPI (irreversible — Roli's button)
python3 -m twine upload dist/langstate-0.1.1*
# prompts for credentials: username __token__, password = pypi-... token
# (or reads ~/.pypirc if configured)

# 3. Yank 0.1.0 (the leaking release) — PyPI has no CLI yank; do it via the web UI:
open https://pypi.org/manage/project/langstate/release/0.1.0/
# → "Options" → "Yank release" → give a reason, e.g.:
#   "0.1.0 sdist shipped internal test fixtures and a retracted TE claim; use 0.1.1"
# Yanking does NOT delete the file (pip can still install it with ==0.1.0 pinned)
# but it hides it from default resolution and flags it in the UI/API.

# 4. Verify
python3 -m venv /tmp/ls-verify && /tmp/ls-verify/bin/pip install langstate
/tmp/ls-verify/bin/python -c "from langstate import compress, validate, __version__; print(__version__)"
# expect: 0.1.1
open https://pypi.org/project/langstate/
```

Old (unscrubbed) `dist/langstate-0.1.0*` artifacts are still present in
`~/dev/langstate/dist/` for reference/diffing — not touched, not deleted.
