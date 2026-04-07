"""Minimal eval tests for the scaffold.

Why this file exists:
It proves the deterministic checks work on the smallest happy-path example
without adding a third-party test runner yet.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentci.evals import evaluate_case


class EvaluateCaseTests(unittest.TestCase):
    def test_required_tools_and_output_can_pass_together(self) -> None:
        case = {
            "id": "case-1",
            "name": "example",
            "input": {"messages": []},
            "tool_fixtures": {},
            "expect": {
                "required_tools": ["jira.get_issue"],
                "forbidden_tools": ["slack.send_message"],
                "critical_tool_sequence": ["jira.get_issue"],
                "output_must_contain": ["Blocked"],
            },
        }
        adapter_output = {
            "final_output": "Blocked because checkout failed.",
            "trace": {
                "case_id": "case-1",
                "events": [
                    {
                        "type": "tool_call",
                        "tool_name": "jira.get_issue"
                    }
                ],
            },
        }

        case_result, regressions = evaluate_case(case, adapter_output)

        self.assertEqual(case_result["status"], "passed")
        self.assertEqual(regressions, [])


if __name__ == "__main__":
    unittest.main()
