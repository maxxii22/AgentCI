"""Reporter tests for CI- and reviewer-facing summaries.

Why this file exists:
It keeps the workflow summary logic testable in Python so the PR-facing output
stays compact and reliable without building extra CLI surface area.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentci.reporter import render_pr_comment


class RenderCISummaryTests(unittest.TestCase):
    def test_pass_summary_is_compact_and_positive(self) -> None:
        run_result = {
            "run_id": "run_pass",
            "git_sha": "abc123",
            "result_kind": "pass",
            "status": "passed",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "summary": {"total": 1, "passed": 1, "failed": 0},
            "cases": [
                {
                    "case_id": "create-followup-ticket",
                    "status": "passed",
                    "duration_ms": 10,
                    "trace_path": "traces/create-followup-ticket.json",
                    "checks": [],
                }
            ],
        }
        regression_report = {
            "run_id": "run_pass",
            "baseline_source": "repo_test_expectations",
            "result_kind": "pass",
            "status": "passed",
            "failed_case_ids": [],
            "summary": {
                "total_cases": 1,
                "passed_cases": 1,
                "failed_cases": 0,
                "blocking_regressions": 0,
                "non_blocking_warnings": 0,
            },
            "regressions": [],
        }

        summary = render_pr_comment(
            run_result,
            regression_report,
            exit_code=0,
            run_url="https://github.com/maxxii22/AgentCI/actions/runs/123",
        )

        self.assertIn("## AgentCI: Pass", summary)
        self.assertIn("Exit code: `0`", summary)
        self.assertIn("Cases: **1** total, **1** passed, **0** failed", summary)
        self.assertIn("Artifacts and logs: [GitHub Actions run](https://github.com/maxxii22/AgentCI/actions/runs/123)", summary)
        self.assertIn("No blocking regressions found.", summary)
        self.assertNotIn("### Failed cases", summary)

    def test_regression_summary_shows_failed_case_and_reason(self) -> None:
        run_result = {
            "run_id": "run_regression",
            "git_sha": "abc123",
            "result_kind": "regression",
            "status": "failed",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "summary": {"total": 1, "passed": 0, "failed": 1},
            "cases": [
                {
                    "case_id": "required-tool-regression-missing-slack",
                    "status": "failed",
                    "duration_ms": 12,
                    "trace_path": "traces/required-tool-regression-missing-slack.json",
                    "checks": [
                        {
                            "name": "required_tools",
                            "status": "failed",
                            "message": "Missing required tools: slack.send_message",
                            "expected": "jira.get_issue, jira.create_issue, slack.send_message",
                            "actual": "jira.get_issue, jira.create_issue",
                        }
                    ],
                }
            ],
        }
        regression_report = {
            "run_id": "run_regression",
            "baseline_source": "repo_test_expectations",
            "result_kind": "regression",
            "status": "failed",
            "failed_case_ids": ["required-tool-regression-missing-slack"],
            "summary": {
                "total_cases": 1,
                "passed_cases": 0,
                "failed_cases": 1,
                "blocking_regressions": 1,
                "non_blocking_warnings": 0,
            },
            "regressions": [
                {
                    "case_id": "required-tool-regression-missing-slack",
                    "severity": "blocking",
                    "check": "required_tools",
                    "reason": "Expected required tools jira.get_issue, jira.create_issue, slack.send_message, but actual tools were jira.get_issue, jira.create_issue. Missing required tools: slack.send_message.",
                    "expected": "jira.get_issue, jira.create_issue, slack.send_message",
                    "actual": "jira.get_issue, jira.create_issue",
                    "message": "Expected required tools jira.get_issue, jira.create_issue, slack.send_message, but actual tools were jira.get_issue, jira.create_issue. Missing required tools: slack.send_message.",
                }
            ],
        }

        summary = render_pr_comment(
            run_result,
            regression_report,
            exit_code=1,
            run_url="https://github.com/maxxii22/AgentCI/actions/runs/456",
        )

        self.assertIn("## AgentCI: Regression detected", summary)
        self.assertIn("Exit code: `1`", summary)
        self.assertIn("`required-tool-regression-missing-slack`", summary)
        self.assertIn("failed check: `required_tools`", summary)
        self.assertIn("expected: `jira.get_issue, jira.create_issue, slack.send_message`", summary)
        self.assertIn("actual: `jira.get_issue, jira.create_issue`", summary)
        self.assertIn("Expected required tools jira.get_issue, jira.create_issue, slack.send_message", summary)
        self.assertIn("### Failed cases", summary)
        self.assertIn("Artifacts and logs: [GitHub Actions run](https://github.com/maxxii22/AgentCI/actions/runs/456)", summary)

    def test_runtime_failure_summary_calls_out_harness_failure(self) -> None:
        run_result = {
            "run_id": "run_error",
            "git_sha": "abc123",
            "result_kind": "runtime_failure",
            "status": "error",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "cases": [],
            "error": {
                "stage": "config",
                "message": "Config file not found: missing-agentci.yaml",
            },
        }
        regression_report = {
            "run_id": "run_error",
            "baseline_source": "repo_test_expectations",
            "result_kind": "runtime_failure",
            "status": "error",
            "failed_case_ids": [],
            "summary": {
                "total_cases": 0,
                "passed_cases": 0,
                "failed_cases": 0,
                "blocking_regressions": 0,
                "non_blocking_warnings": 0,
            },
            "regressions": [],
            "error": {
                "stage": "config",
                "message": "Config file not found: missing-agentci.yaml",
            },
        }

        summary = render_pr_comment(run_result, regression_report, exit_code=2)

        self.assertIn("## AgentCI: Runtime/tooling failure", summary)
        self.assertIn("Exit code: `2`", summary)
        self.assertIn("This is not evidence that product behavior regressed.", summary)
        self.assertIn("Stage: `config`", summary)
        self.assertIn("Config file not found: missing-agentci.yaml", summary)

    def test_pass_summary_does_not_render_noisy_failed_case_section(self) -> None:
        run_result = {
            "run_id": "run_pass",
            "git_sha": "abc123",
            "result_kind": "pass",
            "status": "passed",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "summary": {"total": 2, "passed": 2, "failed": 0},
            "cases": [
                {
                    "case_id": "create-followup-ticket",
                    "status": "passed",
                    "duration_ms": 10,
                    "trace_path": "traces/create-followup-ticket.json",
                    "checks": [],
                },
                {
                    "case_id": "skip-followup-when-not-blocked",
                    "status": "passed",
                    "duration_ms": 9,
                    "trace_path": "traces/skip-followup-when-not-blocked.json",
                    "checks": [],
                },
            ],
        }
        regression_report = {
            "run_id": "run_pass",
            "baseline_source": "repo_test_expectations",
            "result_kind": "pass",
            "status": "passed",
            "failed_case_ids": [],
            "summary": {
                "total_cases": 2,
                "passed_cases": 2,
                "failed_cases": 0,
                "blocking_regressions": 0,
                "non_blocking_warnings": 0,
            },
            "regressions": [],
        }

        summary = render_pr_comment(run_result, regression_report, exit_code=0)

        self.assertNotIn("### Failed cases", summary)
        self.assertNotIn("Failed case IDs", summary)


if __name__ == "__main__":
    unittest.main()
