# COMPLIANCE-DRAFT.md — langstate

**Status:** DRAFT. Internal self-audit artifact generated 2026-04-17 by
`hermes_deliverable`. Not a conformity declaration.

**System:** langstate — `compress(messages)` MVP. Compresses conversation
message history into a language scaffold for stateless-LLM state continuity.
51–54% compression, 6/6 tests. Part of the LPCI research programme. The
compression path calls a local Ollama endpoint (default `localhost:11434`)
for the summarization step via `_summarize_via_ollama()` in `compress.py`.

**Risk classification under EU AI Act:** Not independently high-risk. May be
used inside a high-risk downstream system as a context manager; compliance
posture below assumes that case.

---

## Article 9 — Risk management & data provenance

**Data sources:**
- Caller-provided message history.
- **Ollama summarization call inside the compression path.** `compress.py`
  invokes `_summarize_via_ollama()` against the local Ollama endpoint
  (default `http://localhost:11434`, caller-overridable). The summary is
  inlined verbatim into the scaffold. This is a real side-effect and a real
  attack surface; acknowledged here to correct an earlier draft that claimed
  no network calls.
- No training data. langstate is deterministic over its input **given the
  same Ollama model and response**.
- Caller can swap the summarization model by passing `model=...` and
  `ollama_url=...`.

**Risks identified:**
1. **Information loss from compression.** 46–49% of tokens are discarded by
   design. If the caller relies on full-fidelity replay, langstate is unsuitable.
   Mitigation: publish a "lossless" mode that records raw messages alongside
   the compressed scaffold.
2. **Scaffold becomes stale** as the conversation evolves. Mitigation: caller
   must recompress at a policy-defined cadence.
3. **Reconstruction ambiguity.** The compressed scaffold is NOT a deterministic
   replay of the original messages; it is a state carrier for the stateless LLM.

**Residual risk:** acceptable for session-continuity use. NOT acceptable as a
compliance-grade conversation log (use raw message store for that).

## Article 10 — Data governance

- No PII stored by the library.
- Caller is responsible for redaction before compression.
- No bias testing applies — langstate does not classify, rank, or decide.

## Article 14 — Human oversight & override

- Library is a pure function. No autonomous action. Caller controls
  invocation.
- Override = don't call it.
- Audit trail: caller responsibility. Recommend logging the input message
  count and output scaffold checksum for each call.

## Article 15 — Accuracy, robustness, cybersecurity

- **Accuracy:** compression is not an accuracy-critical task; it's a
  compression-ratio-critical task. Measured at 51–54% on the internal test set.
- **Robustness:** 6/6 tests green. Adversarial inputs (very large message
  histories, malformed structures) not systematically fuzzed. Flagged as gap.
- **Cybersecurity:** outbound HTTP to the caller-configured Ollama endpoint
  (default `localhost:11434`) is the sole network side-effect. No inbound
  surface. No disk writes inside the compression path. Attack surface:
  (a) the Ollama endpoint itself, which must be trusted by the caller; and
  (b) the summary text returned, which is inlined into the scaffold without
  schema validation. Deployer must sanitize or validate summary output
  before feeding the scaffold back into a downstream LLM.
- **Input validation on Ollama response:** not implemented. Gap.

## Article 86 — Right to explanation

langstate does not produce decisions, so Article 86 does not directly apply.
It DOES produce a condensed scaffold; the relationship between input messages
and output scaffold is deterministic and inspectable. A caller can diff the
scaffold against the raw messages to explain what was retained vs. discarded.

## Known limitations (disclosure)

1. Lossy by design. Not a log archive.
2. No robustness fuzzing against malformed input.
3. English-tuned; performance on other languages unmeasured.
4. No formal model registry; caller must pin the Ollama summarization model.
5. No schema validation on the Ollama response that is inlined into the
   scaffold. A malformed or malicious summary reaches the downstream LLM.
6. Not a replacement for structured conversation state (JSON, event log).

## Remediation plan

- Add robustness fuzz harness for message-history edge cases (sprint 1)
- Publish compression-fidelity bench across 5 languages (sprint 2)
- Publish "when NOT to use langstate" decision guide (sprint 1)
