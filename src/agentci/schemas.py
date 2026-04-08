"""Typed data contracts used by the scaffold.

Why this file exists:
It keeps the repo's JSON shapes visible and consistent without adding a heavy
validation dependency before the MVP interface is stable.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class Message(TypedDict):
    role: str
    content: str


class TestCaseExpect(TypedDict, total=False):
    required_tools: list[str]
    forbidden_tools: list[str]
    critical_tool_sequence: list[str]
    output_must_contain: list[str]


class ToolFixture(TypedDict, total=False):
    args: dict[str, Any]
    result: Any


class TestCase(TypedDict):
    id: str
    name: str
    input: dict[str, Any]
    tool_fixtures: dict[str, list[ToolFixture]]
    expect: TestCaseExpect


class TraceEvent(TypedDict, total=False):
    ts: str
    type: str
    role: str
    content: str
    tool_name: str
    args: dict[str, Any]
    result: Any


class Trace(TypedDict):
    case_id: str
    events: list[TraceEvent]


class AdapterOutput(TypedDict):
    final_output: str
    trace: Trace


class CheckResult(TypedDict, total=False):
    name: str
    status: str
    message: str
    reason: str
    expected: str
    actual: str


class CaseResult(TypedDict, total=False):
    case_id: str
    status: str
    duration_ms: int
    trace_path: str
    checks: list[CheckResult]
    failure_reason: str


class RunSummary(TypedDict):
    total: int
    passed: int
    failed: int


class RunResult(TypedDict):
    run_id: str
    git_sha: str
    result_kind: str
    status: str
    started_at: str
    finished_at: str
    summary: RunSummary
    cases: list[CaseResult]
    error: NotRequired["ErrorInfo"]


class RegressionItem(TypedDict):
    case_id: str
    severity: str
    check: str
    reason: str
    expected: str
    actual: str
    message: str


class RegressionSummary(TypedDict):
    total_cases: int
    passed_cases: int
    failed_cases: int
    blocking_regressions: int
    non_blocking_warnings: int


class RegressionReport(TypedDict):
    run_id: str
    baseline_source: str
    result_kind: str
    status: str
    failed_case_ids: list[str]
    summary: RegressionSummary
    regressions: list[RegressionItem]
    error: NotRequired["ErrorInfo"]


class ErrorInfo(TypedDict):
    stage: str
    message: str


class TraceToolStep(TypedDict):
    step: int
    tool_name: str


class TraceFailure(TypedDict):
    check: str
    expected: str
    actual: str
    reason: str


class TraceEvaluation(TypedDict):
    status: str
    summary: str
    failed_checks: list[TraceFailure]


class StoredTrace(TypedDict, total=False):
    case_id: str
    case_name: str
    prompt: str
    input: dict[str, Any]
    expectations: TestCaseExpect
    actual_final_output: str
    actual_tools_used: list[str]
    tool_timeline: list[TraceToolStep]
    evaluation: TraceEvaluation
    failure_reason: str
    raw_trace: Trace
