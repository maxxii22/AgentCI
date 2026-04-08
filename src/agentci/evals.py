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
    required_tools_reason = _required_tools_reason(required_tools, tool_names, missing_tools)
    checks.append(
        _make_check(
            "required_tools",
            not missing_tools,
            required_tools_reason,
            expected=", ".join(required_tools),
            actual=", ".join(tool_names) or "(no tools called)",
        )
    )
    if missing_tools:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="required_tools",
                expected=", ".join(required_tools),
                actual=", ".join(tool_names) or "(no tools called)",
                reason=required_tools_reason or "Missing required tools.",
            )
        )

    forbidden_tools = expectations.get("forbidden_tools", [])
    forbidden_used = [tool for tool in forbidden_tools if tool in tool_names]
    forbidden_tools_reason = _forbidden_tools_reason(forbidden_used)
    checks.append(
        _make_check(
            "forbidden_tools",
            not forbidden_used,
            forbidden_tools_reason,
            expected="No forbidden tools",
            actual=", ".join(forbidden_used) or "(none)",
        )
    )
    if forbidden_used:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="forbidden_tools",
                expected="No forbidden tools",
                actual=", ".join(forbidden_used),
                reason=forbidden_tools_reason or "Forbidden tools were used.",
            )
        )

    expected_sequence = expectations.get("critical_tool_sequence", [])
    sequence_ok = _is_subsequence(expected_sequence, tool_names)
    sequence_reason = _critical_sequence_reason(expected_sequence, tool_names)
    checks.append(
        _make_check(
            "critical_tool_sequence",
            sequence_ok,
            sequence_reason,
            expected=" -> ".join(expected_sequence),
            actual=" -> ".join(tool_names) or "(no tools called)",
        )
    )
    if expected_sequence and not sequence_ok:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="critical_tool_sequence",
                expected=" -> ".join(expected_sequence),
                actual=" -> ".join(tool_names) or "(no tools called)",
                reason=sequence_reason or "Critical tool order regressed.",
            )
        )

    expected_output_facts = expectations.get("output_must_contain", [])
    missing_facts = [
        fact for fact in expected_output_facts if fact.lower() not in final_output.lower()
    ]
    output_reason = _expected_output_reason(expected_output_facts, final_output, missing_facts)
    checks.append(
        _make_check(
            "output_must_contain",
            not missing_facts,
            output_reason,
            expected=", ".join(expected_output_facts),
            actual=final_output or "(empty output)",
        )
    )
    if missing_facts:
        regressions.append(
            _make_regression(
                case_id=case["id"],
                check="output_must_contain",
                expected=", ".join(expected_output_facts),
                actual=final_output or "(empty output)",
                reason=output_reason or "Expected output signal missing.",
            )
        )

    failed_checks = [check for check in checks if check["status"] == "failed"]
    status = "passed" if not failed_checks else "failed"
    case_result: CaseResult = {
        "case_id": case["id"],
        "status": status,
        "duration_ms": 0,
        "trace_path": "",
        "checks": checks,
    }
    if failed_checks:
        case_result["failure_reason"] = " ".join(
            f"{check['name']}: {check.get('reason', check.get('message', 'check failed'))}"
            for check in failed_checks
        )

    return case_result, regressions


def build_regression_report(
    *,
    run_id: str,
    total_cases: int,
    passed_cases: int,
    failed_cases: int,
    regressions: list[RegressionItem],
) -> RegressionReport:
    """Build the JSON report uploaded by CI and rendered in PR comments."""

    failed_case_ids = sorted({regression["case_id"] for regression in regressions})

    return {
        "run_id": run_id,
        "baseline_source": "repo_test_expectations",
        "result_kind": "regression" if regressions else "pass",
        "status": "failed" if regressions else "passed",
        "failed_case_ids": failed_case_ids,
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
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


def _make_check(
    name: str,
    passed: bool,
    reason: str | None,
    *,
    expected: str,
    actual: str,
) -> CheckResult:
    check: CheckResult = {"name": name, "status": "passed" if passed else "failed"}
    if reason:
        check["message"] = reason
    if not passed:
        check["reason"] = reason or "check failed"
        check["expected"] = expected
        check["actual"] = actual
    return check


def _make_regression(
    *,
    case_id: str,
    check: str,
    expected: str,
    actual: str,
    reason: str,
) -> RegressionItem:
    return {
        "case_id": case_id,
        "severity": "blocking",
        "check": check,
        "reason": reason,
        "expected": expected,
        "actual": actual,
        "message": reason,
    }


def _required_tools_reason(
    required_tools: list[str], actual_tools: list[str], missing_tools: list[str]
) -> str | None:
    if not missing_tools:
        return None
    return (
        f"Expected required tools {', '.join(required_tools)}, but actual tools were "
        f"{', '.join(actual_tools) or '(no tools called)'}. Missing required tools: "
        f"{', '.join(missing_tools)}."
    )


def _forbidden_tools_reason(forbidden_used: list[str]) -> str | None:
    if not forbidden_used:
        return None
    return (
        f"Expected no forbidden tools, but actual forbidden tools used were "
        f"{', '.join(forbidden_used)}."
    )


def _critical_sequence_reason(expected_sequence: list[str], actual_tools: list[str]) -> str | None:
    if not expected_sequence or _is_subsequence(expected_sequence, actual_tools):
        return None
    actual_order = " -> ".join(actual_tools) or "(no tools called)"
    return (
        f"Expected tool order {' -> '.join(expected_sequence)}, but actual order was "
        f"{actual_order}."
    )


def _expected_output_reason(
    expected_output_facts: list[str], final_output: str, missing_facts: list[str]
) -> str | None:
    if not missing_facts:
        return None
    actual_output = final_output or "(empty output)"
    return (
        f"Expected final output to contain {', '.join(expected_output_facts)}, but actual "
        f"output was {actual_output}. Missing expected facts: {', '.join(missing_facts)}."
    )


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
