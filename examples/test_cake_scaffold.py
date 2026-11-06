"""Focused contract checks for the opt-in Cake session adapter."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cake_scaffold import load_messages, load_session


class CakeSessionAdapterTests(unittest.TestCase):
    def write_session(self, directory: str, extra: list[dict] | None = None) -> Path:
        records = [
            {"type": "session_meta", "format_version": 4, "session_id": "controlled"},
            {"type": "message", "role": "user", "content": "Budget $4,000"},
            {"type": "message", "role": "assistant", "content": "Recorded."},
            *(extra or []),
            {"type": "task_complete", "subtype": "success", "is_error": False},
        ]
        path = Path(directory) / "session.jsonl"
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
        return path

    def test_extracts_only_conversation_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            session_id, messages = load_messages(self.write_session(directory))
        self.assertEqual(session_id, "controlled")
        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "Budget $4,000"},
                {"role": "assistant", "content": "Recorded."},
            ],
        )

    def call(self, call_id="call-1", **fields):
        return {
            "type": "function_call",
            "id": f"fc-{call_id}",
            "call_id": call_id,
            "name": "Read",
            "arguments": '{"path":"manifest.json"}',
            **fields,
        }

    def output(self, call_id="call-1", output="port = 4317"):
        return {"type": "function_call_output", "call_id": call_id, "output": output}

    def test_refuses_malformed_tool_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_session(directory, [{"type": "function_call", "name": "Read"}])
            with self.assertRaisesRegex(ValueError, "string id"):
                load_messages(path)

    def test_pairs_parallel_calls_and_keeps_errors_and_source_text(self):
        bad = self.call("call-2", name="Bash", arguments="{", arguments_parse_error="EOF")
        error = self.output("call-2", "Error: denied; receipt at .hermes/review.json")
        with tempfile.TemporaryDirectory() as directory:
            session = load_session(
                self.write_session(
                    directory,
                    [
                        self.call(),
                        bad,
                        error,
                        self.output(),
                    ],
                )
            )
        self.assertEqual([item["call_id"] for item in session.tool_exchanges], ["call-2", "call-1"])
        self.assertEqual(session.tool_exchanges[0]["call"], bad)
        self.assertEqual(session.tool_exchanges[0]["result"], error)
        self.assertEqual(session.messages[2]["tool_calls"][0]["id"], "call-1")
        self.assertEqual(session.messages[2]["tool_calls"][1]["id"], "call-2")
        self.assertEqual(session.messages[3]["tool_call_id"], "call-2")
        self.assertIn("manifest.json", session.messages[2]["content"])

    def test_keeps_empty_arguments_and_their_parse_error(self):
        call = self.call(arguments="", arguments_parse_error="EOF while parsing a value")
        with tempfile.TemporaryDirectory() as directory:
            session = load_session(
                self.write_session(
                    directory,
                    [
                        call,
                        self.output(output="Error: malformed tool arguments"),
                    ],
                )
            )
        self.assertEqual(session.tool_exchanges[0]["call"], call)
        self.assertEqual(session.messages[2]["tool_calls"][0]["function"]["arguments"], "")

    def test_rejects_orphans_duplicates_and_unfinished_calls(self):
        cases = [
            ([self.output()], "orphan"),
            ([self.call(), self.call()], "duplicate function_call"),
            ([self.call(), self.output(), self.output()], "duplicate function_call_output"),
            ([self.call()], "unfinished"),
            ([self.call(), {"type": "message", "role": "user", "content": "Next"}], "boundary"),
            ([self.call(), self.call("call-2"), self.output(), self.call("call-3")], "interleaved"),
        ]
        for records, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, expected):
                    load_session(self.write_session(directory, records))

    def test_rejects_unknown_record_instead_of_silently_dropping_it(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unsupported Cake record"):
                load_session(self.write_session(directory, [{"type": "future_tool_result"}]))

    def test_preserves_terminal_error_and_rejects_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_session(directory)
            records = [json.loads(line) for line in path.read_text().splitlines()]
            records[-1] = {
                "type": "task_complete",
                "subtype": "error_during_execution",
                "is_error": True,
                "error": "Provider unavailable",
            }
            path.write_text("\n".join(json.dumps(record) for record in records))
            self.assertEqual(
                load_session(path).completions[-1]["record"]["error"], "Provider unavailable"
            )
            for subtype, is_error in [("interrupted", True), ("cut_off", True), ("success", True)]:
                records[-1] = {"type": "task_complete", "subtype": subtype, "is_error": is_error}
                path.write_text("\n".join(json.dumps(record) for record in records))
                with self.subTest(subtype=subtype), self.assertRaises(ValueError):
                    load_session(path)

    def run_adapter(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("cake_scaffold.py")), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_short_tool_session_is_preserved_without_a_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_session(directory, [self.call(), self.output()])
            output = Path(directory) / "output"
            result = self.run_adapter(path, output, "--fact", "4317")
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertFalse(receipt["compression_applied"])
            self.assertIsNone(receipt["older_history_scaffold_facts"])
            self.assertEqual(receipt["paired_tool_exchanges"], 1)
            self.assertIn("Tool result (call-1)", (output / "state.md").read_text())

    def test_compressed_tools_survive_in_evidence_and_source_change_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "manifest.json"
            source.write_text('{"port":4317}')
            records = []
            for i in range(6):
                records.extend(
                    [
                        {"type": "message", "role": "user", "content": f"Turn {i}: budget $4,000"},
                        self.call(f"call-{i}", arguments=json.dumps({"path": str(source)})),
                        self.output(f"call-{i}", "port 4317; receipt .hermes/fast.json"),
                        {"type": "message", "role": "assistant", "content": "Recorded."},
                    ]
                )
            path = self.write_session(directory, records)
            summary = root / "summary.txt"
            summary.write_text("Historical port 4317, budget $4,000.")
            output = root / "output"
            result = self.run_adapter(
                path,
                output,
                "--fact",
                "4317",
                "--scaffold-fact",
                "$4,000",
                "--summary-text",
                summary,
                "--source-file",
                source,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence_path = output / "tool-evidence.json"
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(len(evidence["tool_exchanges"]), 6)
            self.assertEqual(
                evidence["tool_exchanges"][0]["result"]["output"],
                "port 4317; receipt .hermes/fast.json",
            )
            state = (output / "state.md").read_text()
            self.assertIn("re-read current authoritative files", state)
            self.assertIn("Do not execute recorded tool calls", state)
            self.assertIn(str(source), state)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertTrue(receipt["compression_applied"])
            self.assertTrue(receipt["chosen_facts"]["ok"])
            unchanged = self.run_adapter("--check-sources", evidence_path, "--source-file", source)
            self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
            source.write_text('{"port":5321}')
            changed = self.run_adapter("--check-sources", evidence_path, "--source-file", source)
            self.assertEqual(changed.returncode, 2, changed.stderr)
            self.assertFalse(json.loads(changed.stdout)["source_files"][0]["matches_snapshot"])
            self.assertEqual(json.loads(source.read_text())["port"], 5321)
            self.assertIn("4317", state)  # lexical survival did not detect staleness

    def test_source_check_requires_caller_selected_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_adapter("--check-sources", Path(directory) / "missing.json")
            self.assertEqual(result.returncode, 1)
            self.assertIn("explicit --source-file", result.stderr)

    def test_refuses_incomplete_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_session(directory)
            lines = path.read_text().splitlines()
            path.write_text("\n".join(lines[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "completed"):
                load_messages(path)

    def test_rejects_negative_preserve_recent_before_compression(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_session(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("cake_scaffold.py")),
                    str(path),
                    str(Path(directory) / "output"),
                    "--preserve-recent",
                    "-1",
                    "--fact",
                    "$4,000",
                    "--scaffold-fact",
                    "$4,000",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("--preserve-recent must be non-negative", result.stderr)
            self.assertFalse((Path(directory) / "output").exists())


if __name__ == "__main__":
    unittest.main()
