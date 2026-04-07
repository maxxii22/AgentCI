"""Command adapter runner for the AgentCI scaffold.

Why this file exists:
It defines the single adapter abstraction used in the MVP: send one case to a
command on stdin and read one normalized result from stdout.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentci.schemas import AdapterOutput, TestCase


class AdapterError(RuntimeError):
    """Raised when the agent adapter cannot be executed or parsed."""


def run_command_adapter(command: str, payload: TestCase, cwd: Path) -> AdapterOutput:
    """Execute the configured adapter command and return its parsed JSON output."""

    completed = subprocess.run(
        command,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(cwd),
        shell=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "(no stderr)"
        raise AdapterError(
            f"Adapter command failed with exit code {completed.returncode}: {stderr}"
        )

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdapterError(f"Adapter returned invalid JSON: {error}") from error

    if not isinstance(parsed, dict):
        raise AdapterError("Adapter output must be a JSON object.")
    if "final_output" not in parsed or "trace" not in parsed:
        raise AdapterError("Adapter output must contain `final_output` and `trace`.")

    return parsed  # type: ignore[return-value]
