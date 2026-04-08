"""CLI tests for the local AgentCI run viewer.

Why this file exists:
It verifies that developers can inspect recent runs and case traces quickly
from terminal output without opening raw JSON artifacts.
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


class AgentCIViewTests(unittest.TestCase):
    def test_view_lists_recent_runs(self) -> None:
        output_root = self._make_output_root()
        pass_run_id = self._run_agentci("agentci.yaml", output_root).get("run_id")
        regression_run_id = self._run_agentci(
            "tests/fixtures/regression-agentci.yaml", output_root
        ).get("run_id")

        completed = self._run_view("--output-dir", str(output_root))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Recent AgentCI runs", completed.stdout)
        self.assertIn(str(pass_run_id), completed.stdout)
        self.assertIn(str(regression_run_id), completed.stdout)
        self.assertIn("1 total, 1 passed, 0 failed", completed.stdout)
        self.assertIn("1 total, 0 passed, 1 failed", completed.stdout)

    def test_view_run_shows_failed_case_and_reason(self) -> None:
        output_root = self._make_output_root()
        regression_run_id = str(
            self._run_agentci("tests/fixtures/regression-agentci.yaml", output_root)["run_id"]
        )

        completed = self._run_view(regression_run_id, "--output-dir", str(output_root))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(f"Run: {regression_run_id}", completed.stdout)
        self.assertIn("Status: FAILED", completed.stdout)
        self.assertIn("Cases: 1 total, 0 passed, 1 failed", completed.stdout)
        self.assertIn("required-tool-regression-missing-slack", completed.stdout)
        self.assertIn("Expected required tools", completed.stdout)

    def test_view_case_shows_expected_actual_and_tools(self) -> None:
        output_root = self._make_output_root()
        regression_run_id = str(
            self._run_agentci("tests/fixtures/regression-agentci.yaml", output_root)["run_id"]
        )

        completed = self._run_view(
            regression_run_id,
            "--case",
            "required-tool-regression-missing-slack",
            "--output-dir",
            str(output_root),
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Case: required-tool-regression-missing-slack", completed.stdout)
        self.assertIn("Input:", completed.stdout)
        self.assertIn("Expected:", completed.stdout)
        self.assertIn("Actual:", completed.stdout)
        self.assertIn("Tools used: jira.get_issue, jira.create_issue", completed.stdout)
        self.assertIn("Expected: jira.get_issue, jira.create_issue, slack.send_message", completed.stdout)
        self.assertIn("Actual: jira.get_issue, jira.create_issue", completed.stdout)
        self.assertIn("critical_tool_sequence: jira.get_issue -> slack.send_message", completed.stdout)
        self.assertIn("Reason: Expected required tools", completed.stdout)

    def test_view_latest_uses_most_recent_run(self) -> None:
        output_root = self._make_output_root()
        self._run_agentci("agentci.yaml", output_root)
        regression_run = self._run_agentci("tests/fixtures/regression-agentci.yaml", output_root)

        completed = self._run_view("--latest", "--output-dir", str(output_root))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(f"Run: {regression_run['run_id']}", completed.stdout)

    def _make_output_root(self) -> Path:
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        tempdir = TEMP_ROOT / f"agentci-view-test-{uuid.uuid4().hex}"
        tempdir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)
        return tempdir / "agentci-runs"

    def _run_agentci(self, config_path: str, output_root: Path) -> dict[str, object]:
        completed = self._run_cli(
            "run",
            "--config",
            config_path,
            "--output-dir",
            str(output_root),
        )

        expected_exit = 1 if "regression-agentci.yaml" in config_path else 0
        self.assertEqual(completed.returncode, expected_exit, completed.stdout + completed.stderr)
        run_json = self._latest_run_json(output_root)
        return json.loads(run_json.read_text(encoding="utf-8"))

    def _run_view(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._run_cli("view", *args)

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "agentci.cli", *args],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _latest_run_json(self, output_root: Path) -> Path:
        run_files = sorted(output_root.glob("**/run.json"))
        self.assertTrue(run_files, f"No run.json found under {output_root}")
        return run_files[-1]


if __name__ == "__main__":
    unittest.main()
