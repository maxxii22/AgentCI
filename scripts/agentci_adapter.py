"""Sample adapter command for the internal workflow wedge.

Why this file exists:
It demonstrates the smallest viable adapter contract AgentCI needs today:
read one case from stdin, replay mocked tools, and emit final output plus a
trace to stdout.
"""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from datetime import UTC, datetime
from typing import Any


class FixtureToolRuntime:
    """Replay tool fixtures from the case file and record normalized trace events."""

    def __init__(self, fixtures: dict[str, list[dict[str, Any]]]) -> None:
        self._fixtures = {
            tool_name: deque(entries) for tool_name, entries in fixtures.items()
        }
        self.events: list[dict[str, Any]] = []

    def call(self, tool_name: str, args: dict[str, Any] | None = None) -> Any:
        call_args = args or {}
        self.events.append(
            {
                "ts": _utc_now(),
                "type": "tool_call",
                "tool_name": tool_name,
                "args": call_args,
            }
        )

        if tool_name not in self._fixtures or not self._fixtures[tool_name]:
            raise RuntimeError(f"No remaining fixture for tool: {tool_name}")

        fixture = self._fixtures[tool_name].popleft()
        expected_args = fixture.get("args")
        if expected_args is not None and expected_args != call_args:
            raise RuntimeError(
                f"Fixture args mismatch for {tool_name}: expected {expected_args}, got {call_args}"
            )

        result = fixture.get("result")
        self.events.append(
            {
                "ts": _utc_now(),
                "type": "tool_result",
                "tool_name": tool_name,
                "result": result,
            }
        )
        return result


def main() -> int:
    """Execute the simple internal workflow adapter."""

    case = json.load(sys.stdin)
    user_message = case["input"]["messages"][0]["content"]
    runtime = FixtureToolRuntime(case["tool_fixtures"])

    events = [
        {
            "ts": _utc_now(),
            "type": "message",
            "role": "user",
            "content": user_message,
        }
    ]

    issue_key = _extract_issue_key(user_message)
    issue = runtime.call("jira.get_issue", {"key": issue_key})
    status = str(issue.get("status", "Unknown"))
    summary = str(issue.get("summary", ""))

    if status.lower() == "blocked":
        created_issue = runtime.call(
            "jira.create_issue",
            {"summary": f"Follow-up for {issue_key}: {summary}"},
        )
        final_output = (
            f"{issue_key} is Blocked because {summary}. "
            f"Created follow-up {created_issue.get('key', 'UNKNOWN')}."
        )
    else:
        final_output = f"{issue_key} is not blocked. No follow-up created."

    trace = {
        "case_id": case["id"],
        "events": events
        + runtime.events
        + [
            {
                "ts": _utc_now(),
                "type": "final_output",
                "content": final_output,
            }
        ],
    }

    json.dump({"final_output": final_output, "trace": trace}, sys.stdout)
    sys.stdout.write("\n")
    return 0


def _extract_issue_key(text: str) -> str:
    match = re.search(r"\b[A-Z]+-\d+\b", text)
    if not match:
        raise RuntimeError("Could not find an issue key in the input message.")
    return match.group(0)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
