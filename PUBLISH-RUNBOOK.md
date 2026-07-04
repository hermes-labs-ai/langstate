# langstate — PUBLISH RUNBOOK

_Staged 2026-07-04 (overnight). Everything below the "Two commands" line is pre-flighted and green.
Publishing is a two-command act. Nothing here has been published._

## The two commands (run tomorrow)

```bash
cd ~/dev/langstate
~/hermes-venv/bin/python -m build                       # 1. clean rebuild (wheel + sdist)
~/hermes-venv/bin/python -m twine upload dist/langstate-0.1.0*   # 2. publish to PyPI
```

That's it. Command 2 will prompt for credentials (see prereq).

## One prereq (only thing not done tonight — needs you)

PyPI needs an account + API token; I can't create those.
- Account: https://pypi.org/account/register/ (if you don't have one)
- Token: https://pypi.org/manage/account/token/ → create a token → paste when `twine` prompts
  (username `__token__`, password = the `pypi-…` token), or save it in `~/.pypirc`.

## Verify it worked (30 seconds)

```bash
python3 -m venv /tmp/ls-verify && /tmp/ls-verify/bin/pip install langstate
/tmp/ls-verify/bin/python -c "from langstate import compress, validate; print('ok', __import__('langstate').__version__)"
open https://pypi.org/project/langstate/
```

## Optional post-publish tweak

The README install section still says "PyPI coming soon" (kept honest until publish). To flip it:
```bash
cd ~/dev/langstate
# edit README.md "## Install" → lead with:  pip install langstate
git commit -am "docs: langstate is on PyPI" && git push   # public? private repo today — your call
```

## What was pre-flighted tonight (all green)

- `validate(before, after)` added — the facts-survived receipt; 9 tests, deterministic, no model.
- Default model unified to `qwen3:4b` across compress + adapters + README; "Choosing a model" docs added.
- `anthropic` adapter default → `claude-haiku-4-5` (cheap tier; **confirm the exact model id if you rely on this adapter** — it's opt-in, not the default path).
- `te_check.py` moved out of the shipped package into `bench/` — it was importable-but-broken on install AND bundled internal probe strings (roli/hermes/lpci/seed). **Wheel + sdist verified to no longer contain it or the private corpus.**
- Clean rebuild: `twine check` PASSED on wheel + sdist.
- Fresh-venv install (Python 3.14) → import + `validate` work; test suite 19 passed / 3 Ollama-gated skipped.

## One-way doors (know before you press)

- The **name** `langstate` is claimed forever on your account once uploaded; old versions stay visible.
- You can `yank` a release (`twine`/web UI) but not truly delete it.
- Uploading is irreversible — that's why this is your button to press, not mine.

## Rollback (local, pre-publish)

All tonight's changes are one local commit. To undo before publishing: `git revert <sha>` (sha in REVERT-LEDGER.md).
