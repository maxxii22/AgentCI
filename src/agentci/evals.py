"""Deterministic evaluation checks for the scaffold.

Why this file exists:
It contains the low-noise merge-blocking checks we want in the first MVP and
keeps policy decisions separate from command execution.
"""

from __future__ import annotations

from agentci.schemas import (
    AdapterOutput,
    CaseResult,
    CheckResult,
    RegressionItem,
    RegressionReport,
    TestCase,
)


def evaluate_case(case: TestCase, adapter_output: AdapterOutput) -> tuple[CaseResult, list[RegressionItem]]:
    """Evaluate one case and return both case status and blocking regressions."""

    trace = adapter_output["trace"]
    final_output = adapter_output["final_output"]
    tool_names = _extract_tool_names(trace.get("events", []))
    expectations = case.get("expect", {})

    checks: list[CheckResult] = []
    regressions: list[RegressionItem] = []

    required_tools = expectations.get("required_tools", [])
    missing_tools = [tool for tool in required_tools if tool not in tool_names]
    checks.append(_make_check("required_tools", not missing_tools, _join_items(missing_tools)))
    if missing_tools:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="required_tools",
                expected=", ".join(required_tools),
                actual=", ".join(tool_names) or "(no tools called)",
                message=f"Missing required tools: {', '.join(missing_tools)}",
            )
        )

    forbidden_tools = expectations.get("forbidden_tools", [])
    forbidden_used = [tool for tool in forbidden_tools if tool in tool_names]
    checks.append(_make_check("forbidden_tools", not forbidden_used, _join_items(forbidden_used)))
    if forbidden_used:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="forbidden_tools",
                expected="No forbidden tools",
                actual=", ".join(forbidden_used),
                message=f"Forbidden tools were used: {', '.join(forbidden_used)}",
            )
        )

    expected_sequence = expectations.get("critical_tool_sequence", [])
    sequence_ok = _is_subsequence(expected_sequence, tool_names)
    checks.append(
        _make_check(
            "critical_tool_sequence",
            sequence_ok,
            None if sequence_ok else f"Expected subsequence: {' -> '.join(expected_sequence)}",
        )
    )
    if expected_sequence and not sequence_ok:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="critical_tool_sequence",
                expected=" -> ".join(expected_sequence),
                actual=" -> ".join(tool_names) or "(no tools called)",
                message="Critical tool order regressed.",
            )
        )

    expected_output_facts = expectations.get("output_must_contain", [])
    missing_facts = [
        fact for fact in expected_output_facts if fact.lower() not in final_output.lower()
    ]
    checks.append(
        _make_check("output_must_contain", not missing_facts, _join_items(missing_facts))
    )
    if missing_facts:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="output_must_contain",
                expected=", ".join(expected_output_facts),
                actual=final_output,
                message=f"Missing expected facts: {', '.join(missing_facts)}",
            )
        )

    status = "passed" if all(check["status"] == "passed" for check in checks) else "failed"
    case_result: CaseResult = {
        "case_id": case["id"],
        "status": status,
        "duration_ms": 0,
        "trace_path": "",
        "checks": checks,
    }

    return case_result, regressions


def build_regression_report(run_id: str, regressions: list[RegressionItem]) -> RegressionReport:
    """Build the JSON report uploaded by CI and rendered in PR comments."""

    return {
        "run_id": run_id,
        "baseline_source": "repo_test_expectations",
        "status": "failed" if regressions else "passed",
        "summary": {
            "blocking_regressions": len(regressions),
            "non_blocking_warnings": 0,
        },
        "regressions": regressions,
    }


def _extract_tool_names(events: list[dict[str, object]]) -> list[str]:
    return [
        str(event.get("tool_name", ""))
        for event in events
        if event.get("type") == "tool_call" and event.get("tool_name")
    ]


def _make_check(name: str, passed: bool, message: str | None) -> CheckResult:
    check: CheckResult = {"name": name, "status": "passed" if passed else "failed"}
    if message:
        check["message"] = message
    return check


def _make_regression(
    *,
    case_id: str,
    check: str,
    expected: str,
    actual: str,
    message: str,
) -> RegressionItem:
    return {
        "case_id": case_id,
        "severity": "blocking",
        "check": check,
        "expected": expected,
        "actual": actual,
        "message": message,
    }


def _join_items(items: list[str]) -> str | None:
    return ", ".join(items) if items else None


def _is_subsequence(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return True

    index = 0
    for tool_name in actual:
        if tool_name == expected[index]:
            index += 1
            if index == len(expected):
                return True

    return False
