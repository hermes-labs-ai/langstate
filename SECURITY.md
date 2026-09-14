# Security Policy

## Scope

langstate is a functional prototype/library for compressing LLM conversations
and validating literal facts (see [README.md's Boundaries and current
evidence](README.md#boundaries-and-current-evidence)). It is not a lossless
archive, a structured state store, or production infrastructure, and
`validate()` checks literal text only — it does not establish semantic
equivalence. Security reports should concern langstate's own code (for
example, an adapter mishandling an API key or environment variable, or a
`validate` result that is wrong on its own literal-match terms), not the
accuracy or safety of a third-party model's summarization.

## Reporting a Vulnerability

**Do not open a public issue for security-relevant reports.**

Instead, email: **roli@hermes-labs.ai**

Include:
- A description of the vulnerability.
- Steps to reproduce the issue.
- Any relevant logs or output.

## Response Timeline

langstate is maintained by a single maintainer, on a best-effort basis:

- **Acknowledgment**: within 48 hours of your report.
- **Assessment**: within 7 days we will confirm the issue and outline next steps.
- **Fix**: we aim to release a patch within 30 days of confirmation. This is
  a best-effort target, not a guaranteed SLA.

## Supported Versions

Security fixes are applied to the latest release only.

Thank you for helping keep langstate's stated scope honest.
