# Historical compliance draft — not a current assessment

This file is retained only to mark an earlier internal draft as superseded. It
is not a conformity declaration, legal analysis, release criterion, or evidence
of deployment.

For the current product boundary, use the README: langstate is an experimental,
lossy context-compression library. It calls a caller-selected summarizer, places
the returned text in a scaffold message, and can report whether caller-selected
literal strings occur in the result.

Important limits:

- A summary may omit, distort, or add information.
- The lexical receipt does not establish semantic equivalence or safety.
- Callers remain responsible for message handling, data protection, model
  selection, and downstream use.
- Do not use the library as a substitute for raw records, structured state, or
  a compliance-grade audit trail.
