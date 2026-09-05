# Benchmark artifact provenance

The repository-root `bench_results.json`, `bench_openai.json`, and
`bench_anthropic.json` are preserved historical single-run artifacts. They are
not evidence for the current `langstate` package or release.

Exact source record:

| Artifact | SHA-256 | First tracked commit |
|---|---|---|
| `bench_results.json` | `9e412bf0303ea3b473ea95cd3027b3a7a14c866529b434ff1289e2c4f0560065` | `9084a76808926b352f94be3be275518549ab7819` |
| `bench_openai.json` | `53fac5a0cc2e95b1228989968c1591d2761e865037a4ba883b890cda5c9718b3` | `9084a76808926b352f94be3be275518549ab7819` |
| `bench_anthropic.json` | `dcce87a491a0a745ce35d9307b84c0ab962ab0c058117fb228363bd951c02ffb` | `9084a76808926b352f94be3be275518549ab7819` |

Why they are excluded from current claims:

- The JSON does not record a run time, source commit, full model identifier, or
  reproducible decoding/runtime configuration.
- `bench_adapters.py` imports the legacy repository-root `adapters.py` and
  `compress.py`, not the shipping modules under `src/langstate/`; both pairs
  differ at current `main` commit
  `b9a8b036ab65d0a74d27a580602cd12afd438235`.
- `bench_results.json` names missing-fact keys such as `corpus_size`,
  `arxiv_papers`, and `benchmarks` that are not in the current runner's
  `GROUND_TRUTH` list. The current script therefore cannot reproduce the stored
  row as written.
- Adapter output is model-generated and is not deterministic. Re-running it
  without a fixed model snapshot and full run manifest would produce another
  observation, not repair the provenance of these bytes.

`MANIFEST.in` and the src-layout build exclude these files from both the wheel
and sdist. Keep them as historical leads only. The current exercised contract
is the deterministic, literal-text `validate(...)` receipt described in the
README; it is lexical evidence, not semantic-preservation evidence.
