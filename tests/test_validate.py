"""Tests for langstate.validate — the facts-survived receipt. No model required."""

from langstate import compress, validate
from langstate.validate import Receipt, extract_facts


def _fixed_summary(text: str) -> str:
    """Deterministic fake summarizer: keeps two facts, drops the rest — lets us
    exercise compress+validate end to end without a live model."""
    return "Budget capped at $4,000. Launch scheduled for May 5. Roli leads Hermes Labs."


def test_explicit_facts_all_survive():
    before = [{"role": "user", "content": "budget is $4,000 and launch is May 5"}]
    after = [{"role": "system", "content": "Budget $4,000; launch May 5"}]
    r = validate(before, after, facts=["$4,000", "May 5"])
    assert r.ok and bool(r) is True
    assert r.survival_rate == 1.0
    assert r.dropped == []
    assert r.total == 2
    assert isinstance(r, Receipt)


def test_dropped_fact_flags_not_ok():
    before = [{"role": "user", "content": "the launch budget is $2,000 and status is pending"}]
    after = [{"role": "system", "content": "the launch budget is $2,000"}]
    r = validate(before, after, facts=["$2,000", "pending"])
    assert not r.ok and bool(r) is False
    assert "pending" in r.dropped
    assert "$2,000" in r.survived
    assert 0.0 < r.survival_rate < 1.0


def test_auto_extract_finds_salient_tokens():
    facts = extract_facts("Dana runs Kite Labs; the CLI gives 2.5x at 90.1% with a $2,000 budget.")
    joined = " ".join(facts).lower()
    for needle in ["dana", "kite labs", "2.5x", "90.1%", "$2,000"]:
        assert needle in joined, f"{needle} not extracted from {facts}"


def test_auto_extract_does_not_consume_money_suffix_or_duplicate_digits():
    facts = extract_facts("Dana controls a $4,000 budget.")
    assert facts == ["$4,000", "Dana"]


def test_lexical_receipt_does_not_claim_semantic_attribution():
    before = [{"role": "user", "content": "Dana controls a $4,000 budget."}]
    after = [{"role": "system", "content": "Dana controls no budget. Pat controls the $4,000 budget."}]
    receipt = validate(before, after, facts=["Dana", "$4,000"])
    assert receipt.ok  # token presence only; callers must not treat this as semantic proof


def test_auto_extract_is_default_path():
    before = [{"role": "user", "content": "dataset is 12MB with 40 files"}]
    after = [{"role": "system", "content": "dataset is 12MB with 40 files"}]
    r = validate(before, after)  # no explicit facts -> auto extract
    assert r.total > 0
    assert r.ok  # everything present verbatim in after


def test_case_insensitive_survival():
    before = [{"role": "user", "content": "Company is Hermes Labs"}]
    after = [{"role": "system", "content": "company: hermes labs"}]
    r = validate(before, after, facts=["Hermes Labs"])
    assert r.ok


def test_empty_before_and_after():
    r = validate([], [])
    assert r.ok and r.total == 0 and r.survival_rate == 1.0


def test_summary_reports_counts_and_drops():
    before = [{"role": "user", "content": "$2,000 budget, status pending"}]
    after = [{"role": "system", "content": "$2,000 budget"}]
    r = validate(before, after, facts=["$2,000", "pending"])
    s = r.summary()
    assert "1/2" in s and "DROPPED" in s and "pending" in s


def test_receipt_as_dict_roundtrips_fields():
    r = validate(
        [{"role": "user", "content": "x is 42"}],
        [{"role": "system", "content": "x is 42"}],
        facts=["42"],
    )
    d = r.as_dict()
    assert d["ok"] is True and d["survived"] == ["42"] and d["dropped"] == []
    assert 0.0 <= d["survival_rate"] <= 1.0


def test_end_to_end_with_fake_summarizer():
    msgs = [{"role": "system", "content": "sys"}]
    for i in range(20):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"turn {i} filler chatter"})
    # inject facts into early (compressed-away) history
    msgs[1]["content"] = "budget is $4,000"
    msgs[3]["content"] = "launch is May 5"
    compressed = compress(msgs, summarizer=_fixed_summary, preserve_recent=2)
    r = validate(msgs, compressed, facts=["$4,000", "May 5"])
    assert r.ok, r.summary()
    assert r.token_reduction > 0
