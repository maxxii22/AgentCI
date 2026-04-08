"""End-to-end CLI tests for the Day 3-5 refocus.

Why this file exists:
It verifies the exact MVP slice we care about right now: `agentci run` should
return the right exit code and write artifacts for pass, regression, and
runtime/config failure paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMP_ROOT = REPO_ROOT / ".tmp-tests"


class AgentCIRunTests(unittest.TestCase):
    def test_run_passes_for_default_sample_config(self) -> None:
        completed, output_root = self._run_cli(
            "--config",
            "agentci.yaml",
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        run_json = self._latest_run_json(output_root)
        run_data = json.loads(run_json.read_text(encoding="utf-8"))
        trace_data = json.loads(
            (run_json.parent / "traces" / "create-followup-ticket.json").read_text(encoding="utf-8")
        )
        self.assertEqual(run_data["status"], "passed")
        self.assertEqual(run_data["result_kind"], "pass")
        self.assertEqual(run_data["summary"]["total"], 1)
        self.assertTrue((run_json.parent / "traces" / "create-followup-ticket.json").exists())
        self.assertEqual(trace_data["case_id"], "create-followup-ticket")
        self.assertEqual(
            trace_data["prompt"],
            "Review issue OPS-42 and create a follow-up task if it is blocked.",
        )
        self.assertEqual(trace_data["actual_tools_used"], ["jira.get_issue", "jira.create_issue"])
        self.assertEqual(
            trace_data["tool_timeline"],
            [
                {"step": 1, "tool_name": "jira.get_issue"},
                {"step": 2, "tool_name": "jira.create_issue"},
            ],
        )
        self.assertEqual(trace_data["evaluation"]["status"], "passed")
        self.assertEqual(trace_data["evaluation"]["failed_checks"], [])
        self.assertEqual(
            trace_data["actual_final_output"],
            "OPS-42 is Blocked because Checkout fails on Safari. Created follow-up OPS-99.",
        )
        self.assertIn("raw_trace", trace_data)

    def test_run_returns_exit_code_1_for_intentional_regression_fixture(self) -> None:
        completed, output_root = self._run_cli(
            "--config",
            "tests/fixtures/regression-agentci.yaml",
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)

        run_json = self._latest_run_json(output_root)
        report_json = run_json.parent / "regression-report.json"
        trace_json = run_json.parent / "traces" / "required-tool-regression-missing-slack.json"
        run_data = json.loads(run_json.read_text(encoding="utf-8"))
        report_data = json.loads(report_json.read_text(encoding="utf-8"))
        trace_data = json.loads(trace_json.read_text(encoding="utf-8"))

        self.assertEqual(run_data["status"], "failed")
        self.assertEqual(run_data["result_kind"], "regression")
        self.assertIn("failure_reason", run_data["cases"][0])
        self.assertIn("Missing required tools: slack.send_message", run_data["cases"][0]["failure_reason"])
        self.assertEqual(report_data["status"], "failed")
        self.assertEqual(report_data["result_kind"], "regression")
        self.assertGreaterEqual(report_data["summary"]["blocking_regressions"], 1)
        self.assertEqual(report_data["failed_case_ids"], ["required-tool-regression-missing-slack"])
        self.assertEqual(report_data["summary"]["failed_cases"], 1)
        self.assertTrue((run_json.parent / "traces" / "required-tool-regression-missing-slack.json").exists())

        first_regression = report_data["regressions"][0]
        self.assertEqual(first_regression["case_id"], "required-tool-regression-missing-slack")
        self.assertEqual(first_regression["check"], "required_tools")
        self.assertEqual(first_regression["expected"], "jira.get_issue, jira.create_issue, slack.send_message")
        self.assertEqual(first_regression["actual"], "jira.get_issue, jira.create_issue")
        self.assertEqual(first_regression["reason"], first_regression["message"])
        self.assertIn("Expected required tools", first_regression["reason"])
        self.assertIn("Missing required tools: slack.send_message", first_regression["reason"])

        self.assertEqual(trace_data["case_id"], "required-tool-regression-missing-slack")
        self.assertEqual(trace_data["evaluation"]["status"], "failed")
        self.assertIn("blocking check(s) failed", trace_data["evaluation"]["summary"])
        self.assertEqual(trace_data["actual_tools_used"], ["jira.get_issue", "jira.create_issue"])
        self.assertIn("failure_reason", trace_data)
        self.assertIn("Missing required tools: slack.send_message", trace_data["failure_reason"])
        first_failed_check = trace_data["evaluation"]["failed_checks"][0]
        self.assertEqual(first_failed_check["check"], "required_tools")
        self.assertEqual(
            first_failed_check["expected"],
            "jira.get_issue, jira.create_issue, slack.send_message",
        )
        self.assertEqual(first_failed_check["actual"], "jira.get_issue, jira.create_issue")
        self.assertIn("Expected required tools", first_failed_check["reason"])

    def test_run_returns_exit_code_2_for_config_failure_and_writes_error_artifacts(self) -> None:
        completed, output_root = self._run_cli(
            "--config",
            "missing-agentci.yaml",
        )

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)

        run_json = self._latest_run_json(output_root)
        report_json = run_json.parent / "regression-report.json"
        run_data = json.loads(run_json.read_text(encoding="utf-8"))
        report_data = json.loads(report_json.read_text(encoding="utf-8"))

        self.assertEqual(run_data["status"], "error")
        self.assertEqual(run_data["result_kind"], "runtime_failure")
        self.assertEqual(run_data["error"]["stage"], "config")
        self.assertEqual(report_data["status"], "error")
        self.assertEqual(report_data["result_kind"], "runtime_failure")

    def _run_cli(self, *args: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        tempdir = TEMP_ROOT / f"agentci-test-{uuid.uuid4().hex}"
        tempdir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)

        output_root = tempdir / "agentci-runs"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentci.cli",
                "run",
                *args,
                "--output-dir",
                str(output_root),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        return completed, output_root

    def _latest_run_json(self, output_root: Path) -> Path:
        run_files = sorted(output_root.glob("**/run.json"))
        self.assertTrue(run_files, f"No run.json found under {output_root}")
        return run_files[-1]


if __name__ == "__main__":
    unittest.main()
