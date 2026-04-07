"""Load repo-local JSON test cases.

Why this file exists:
It keeps file discovery and basic schema validation separate from the runner so
the execution path stays easy to reason about.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentci.schemas import TestCase


class LoaderError(ValueError):
    """Raised when a test case file cannot be loaded or validated."""


def load_test_cases(root_dir: Path, pattern: str) -> list[TestCase]:
    """Load and minimally validate test cases from the configured glob."""

    paths = sorted(root_dir.glob(pattern))
    if not paths:
        raise LoaderError(f"No test cases matched: {pattern}")

    cases: list[TestCase] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise LoaderError(f"Invalid JSON in {path}: {error}") from error

        _validate_test_case(path, data)
        cases.append(data)

    return cases


def _validate_test_case(path: Path, data: object) -> None:
    if not isinstance(data, dict):
        raise LoaderError(f"Test case {path} must be a JSON object.")

    required_keys = {"id", "name", "input", "tool_fixtures", "expect"}
    missing_keys = sorted(required_keys - set(data.keys()))
    if missing_keys:
        raise LoaderError(f"Test case {path} is missing keys: {', '.join(missing_keys)}")
