"""Small, deterministic command-line entry point for Langstate."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from . import __version__, compress, validate


def _demo_summary(_: str) -> str:
    return "- Project: Atlas\\n- Budget: $4,000"


def _demo_payload() -> dict[str, object]:
    before = [
        {"role": "system", "content": "Preserve named project facts."},
        {"role": "user", "content": "The project is Atlas."},
        {"role": "assistant", "content": "Recorded Project: Atlas."},
        {"role": "user", "content": "The budget is $4,000."},
        {"role": "assistant", "content": "Recorded Budget: $4,000."},
        {"role": "user", "content": "What remains?"},
        {"role": "assistant", "content": "Review the release packet."},
    ]
    after = compress(
        before,
        min_turns_to_compress=2,
        preserve_recent=1,
        summarizer=_demo_summary,
    )
    receipt = validate(before, after, facts=["Project: Atlas", "Budget: $4,000"])
    return {"compressed_messages": after, "receipt": receipt.as_dict()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspectable context compression.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="run a deterministic local compression receipt")
    args = parser.parse_args(argv)
    if args.command == "demo":
        print(json.dumps(_demo_payload(), indent=2, sort_keys=True))
        return 0
    parser.error("unknown command")
    return 2
