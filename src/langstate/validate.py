"""
langstate.validate — the facts-survived receipt.

``compress`` shrinks a conversation; ``validate`` records whether selected
literal strings occur in the output. It has zero dependencies, makes no model
call, and is fully deterministic, so it can run in CI.

    from langstate import compress, validate

    compressed = compress(messages)
    receipt = validate(messages, compressed)     # auto-extract salient facts
    print(receipt.summary())                     # "18/20 facts survived (90%) ..."
    assert receipt.ok                            # or gate on receipt.survival_rate

    # Or check the specific facts you actually care about:
    receipt = validate(messages, compressed,
                       facts=["$4,000 budget", "launch May 5", "Acme Corp"])
    for fact in receipt.dropped:
        print("LOST:", fact)

"Survived" means only that a selected string's normalized text occurs in the
compressed messages. This lexical check cannot credit a paraphrase and cannot
detect changed attribution, negation, or meaning when the same tokens remain.
A green receipt is therefore not semantic-equivalence proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WS = re.compile(r"\s+")

# Salient-fact patterns. Deliberately conservative: money, ratios, percentages,
# multi-digit numbers, acronyms, and proper nouns — the token classes that carry
# decisions, quantities, and named entities.
_MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[kKmMbB]\b)?")
_RATIO = re.compile(r"\b\d+(?:\.\d+)?x\b")
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s?%")
_NUMBER = re.compile(r"\b\d[\d,]*\.\d+\b|\b\d{2,}\b")
_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*\b")
_PROPER = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

# Capitalized sentence-openers / filler we don't want to treat as facts.
_PROPER_STOP = {
    "the", "we", "our", "it", "that", "this", "how", "what", "a", "i", "let",
    "one", "and", "so", "yes", "no", "actually", "makes", "wait", "perfect",
    "good", "thanks", "go", "ok", "okay", "submit", "focus", "open", "position",
    "correct", "true", "smart", "nice", "your", "you", "they", "who", "when",
    "here", "there", "now", "then", "same", "different", "budget",
}


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().lower()


def _messages_text(messages: list[dict]) -> str:
    return "\n".join(m.get("content", "") or "" for m in messages)


def _approx_tokens(messages: list[dict]) -> int:
    """Rough token count (~4 chars/token), matching langstate.compress."""
    return sum(len(m.get("content", "") or "") // 4 for m in messages)


def extract_facts(text: str) -> list[str]:
    """Heuristically pull salient facts (money, ratios, %, multi-digit numbers,
    acronyms, proper nouns) from text. Order-preserving, de-duplicated on the
    normalized form.

    This powers the auto path of :func:`validate`. It is a heuristic — for a
    precise receipt, pass an explicit ``facts=[...]`` list instead.
    """
    facts: list[str] = []
    seen: set[str] = set()

    def add(tok: str) -> None:
        tok = tok.strip().strip(".,;:")
        if not tok:
            return
        key = _norm(tok)
        if not key or key in seen:
            return
        seen.add(key)
        facts.append(tok)

    covered: list[tuple[int, int]] = []
    for pat in (_MONEY, _RATIO, _PERCENT, _NUMBER, _ACRONYM):
        for m in pat.finditer(text):
            if any(m.start() >= start and m.end() <= end for start, end in covered):
                continue
            add(m.group(0))
            covered.append(m.span())
    for m in _PROPER.finditer(text):
        tok = m.group(0)
        if " " not in tok and _norm(tok) in _PROPER_STOP:
            continue
        add(tok)
    return facts


@dataclass
class Receipt:
    """Result of a facts-survived check. Truthy iff nothing was dropped."""

    facts_checked: list[str]
    survived: list[str]
    dropped: list[str]
    tokens_before: int = 0
    tokens_after: int = 0

    @property
    def total(self) -> int:
        return len(self.facts_checked)

    @property
    def survival_rate(self) -> float:
        return len(self.survived) / self.total if self.total else 1.0

    @property
    def token_reduction(self) -> float:
        if not self.tokens_before:
            return 0.0
        return 1.0 - (self.tokens_after / self.tokens_before)

    @property
    def ok(self) -> bool:
        return not self.dropped

    def __bool__(self) -> bool:
        return self.ok

    def summary(self) -> str:
        pct = round(self.survival_rate * 100)
        red = round(self.token_reduction * 100)
        head = f"{len(self.survived)}/{self.total} facts survived ({pct}%) · {red}% smaller"
        if self.dropped:
            head += f" · DROPPED: {', '.join(self.dropped)}"
        return head

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "survived": list(self.survived),
            "dropped": list(self.dropped),
            "survival_rate": round(self.survival_rate, 4),
            "token_reduction": round(self.token_reduction, 4),
            "ok": self.ok,
        }


def validate(
    before: list[dict],
    after: list[dict],
    facts: list[str] | None = None,
) -> Receipt:
    """Check which facts from ``before`` survived compression into ``after``.

    Args:
        before: original messages (pre-compression).
        after: compressed messages returned by :func:`langstate.compress`.
        facts: optional explicit list of fact strings to check. If ``None``,
            facts are auto-extracted from ``before`` via :func:`extract_facts`
            (heuristic — pass an explicit list for a precise receipt).

    Returns:
        A :class:`Receipt`. A fact "survived" if its normalized text is a
        substring of the concatenated, normalized ``after`` content. This is a
        lexical presence check, not a semantic-equivalence check.
    """
    if facts is None:
        facts = extract_facts(_messages_text(before))

    after_text = _norm(_messages_text(after))
    survived: list[str] = []
    dropped: list[str] = []
    for fact in facts:
        key = _norm(fact)
        if key and key in after_text:
            survived.append(fact)
        else:
            dropped.append(fact)

    return Receipt(
        facts_checked=list(facts),
        survived=survived,
        dropped=dropped,
        tokens_before=_approx_tokens(before),
        tokens_after=_approx_tokens(after),
    )
