"""langstate.te_check — RETRACTED.

This module used to compute a "behavioral transfer-entropy proxy" against a
synthetic corpus, framing a near-zero recall delta as evidence for a
transfer-entropy claim. That claim and its framing are retracted (it was a
code-derived artifact, not a validated result) — see CHANGELOG.md v0.1.1 and
never cite it externally.

This file is kept only as a placeholder so old imports fail loudly instead of
silently reproducing the retracted claim. It intentionally has no PROBES list
and no proxy computation, and it is excluded from the published package via
MANIFEST.in (`global-exclude te_check.py`).

The externally-safe, still-citable claim for langstate is:

    2.5x compression @ 0.846 recall (n=74)

Do not reintroduce transfer-entropy or Markov-sufficiency framing here.
"""

raise ImportError(
    "langstate.te_check is retracted and no longer provides a working "
    "benchmark. See CHANGELOG.md v0.1.1."
)
