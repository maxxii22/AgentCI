"""Local terminal viewer for AgentCI run artifacts.

Why this file exists:
It lets developers inspect recent runs and per-case traces quickly without
opening raw JSON files or building a dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentci.reporter import load_run_and_regression_artifacts
from agentci.schemas import RegressionReport, RunResult, StoredTrace


class ViewError(RuntimeError):
    """Raised when a requested run or case cannot be displayed."""


def list_runs(output_root: Path) -> str:
    """Render a clean list of recent runs beneath the output directory."""

    runs = discover_runs(output_root)
    if not runs:
        raise ViewError(f"No AgentCI runs found under: {output_root}")

    lines = [
        "Recent AgentCI runs",
        f"Output dir: {output_root}",
        "",
    ]
    for run_dir, run_result in runs:
        summary = run_result["summary"]
        lines.append(
            f"- {run_result['run_id']} | {run_result['started_at']} | {run_result['status'].upper()} | "
            f"{summary['total']} total, {summary['passed']} passed, {summary['failed']} failed"
        )
    return "\n".join(lines)


def view_run(output_root: Path, run_id: str | None = None, *, latest: bool = False) -> str:
    """Render a human-readable summary for one run."""

    run_dir, run_result, regression_report = load_run_bundle(
        output_root,
        run_id=run_id,
        latest=latest,
    )
    failed_items = _failed_items(regression_report)

    summary = run_result["summary"]
    lines = [
        f"Run: {run_result['run_id']}",
        f"Status: {run_result['status'].upper()}",
        f"Result: {run_result.get('result_kind', 'pass')}",
        f"Started: {run_result['started_at']}",
        f"Finished: {run_result['finished_at']}",
        f"Cases: {summary['total']} total, {summary['passed']} passed, {summary['failed']} failed",
        "",
        "Cases:",
    ]

    for case in run_result["cases"]:
        lines.append(f"- {case['case_id']}: {case['status'].upper()}")
        if case["status"] == "failed":
            lines.append(f"  Reason: {case.get('failure_reason', 'Blocking checks failed.')}")

    if "error" in run_result:
        error = run_result["error"]
        lines.extend(
            [
                "",
                "Run error:",
                f"- Stage: {error['stage']}",
                f"- Message: {error['message']}",
            ]
        )

    if failed_items:
        lines.extend(["", "Failed cases:"])
        for item in failed_items:
            lines.append(f"- {item['case_id']}")
            lines.append(f"  Check: {item['check']}")
            lines.append(f"  Reason: {item['reason']}")

    lines.extend(["", f"Artifacts: {run_dir}"])
    return "\n".join(lines)


def view_case(
    output_root: Path,
    *,
    case_id: str,
    run_id: str | None = None,
    latest: bool = False,
) -> str:
    """Render a concise case-level view from the saved trace artifact."""

    run_dir, run_result, regression_report = load_run_bundle(
        output_root,
        run_id=run_id,
        latest=latest,
    )
    case_result = next((case for case in run_result["cases"] if case["case_id"] == case_id), None)
    if case_result is None:
        raise ViewError(f"Case not found in run {run_result['run_id']}: {case_id}")

    trace_path = run_dir / str(case_result["trace_path"])
    if not trace_path.exists():
        raise ViewError(f"Trace artifact not found for case {case_id}: {trace_path}")

    trace = _read_trace(trace_path)
    failed_items = [item for item in _failed_items(regression_report) if item["case_id"] == case_id]

    lines = [
        f"Run: {run_result['run_id']}",
        f"Case: {case_id}",
        f"Status: {case_result['status'].upper()}",
        "",
        "Input:",
        f"- Prompt: {trace.get('prompt', '(no prompt recorded)')}",
        "",
        "Expected:",
    ]

    expectations = trace.get("expectations", {})
    if expectations:
        for key, value in expectations.items():
            lines.append(f"- {key}: {_format_expectation(key, value)}")
    else:
        lines.append("- (no explicit expectations)")

    lines.extend(
        [
            "",
            "Actual:",
            f"- Final output: {trace.get('actual_final_output', '(no final output)')}",
            f"- Tools used: {', '.join(trace.get('actual_tools_used', [])) or '(none)'}",
        ]
    )

    tool_timeline = trace.get("tool_timeline", [])
    if tool_timeline:
        lines.append(
            "- Tool timeline: "
            + ", ".join(f"{step['step']}. {step['tool_name']}" for step in tool_timeline)
        )

    if failed_items:
        lines.extend(["", "Failure:"])
        for item in failed_items:
            lines.append(f"- Check: {item['check']}")
            lines.append(f"  Expected: {item['expected']}")
            lines.append(f"  Actual: {item['actual']}")
            lines.append(f"  Reason: {item['reason']}")
    else:
        lines.extend(["", "Failure:", "- None. All blocking checks passed."])

    lines.extend(["", f"Trace: {trace_path}"])
    return "\n".join(lines)


def discover_runs(output_root: Path) -> list[tuple[Path, RunResult]]:
    """Find saved runs and sort newest-first."""

    run_paths = sorted(output_root.glob("**/run.json"))
    bundles: list[tuple[Path, RunResult]] = []
    for run_path in run_paths:
        run_result = _read_run_result(run_path)
        bundles.append((run_path.parent, run_result))
    bundles.sort(key=lambda item: item[1]["started_at"], reverse=True)
    return bundles


def load_run_bundle(
    output_root: Path,
    *,
    run_id: str | None,
    latest: bool,
) -> tuple[Path, RunResult, RegressionReport]:
    """Load one run bundle from the output directory."""

    runs = discover_runs(output_root)
    if not runs:
        raise ViewError(f"No AgentCI runs found under: {output_root}")

    if latest or run_id is None:
        run_dir, run_result = runs[0]
        regression_report = load_run_and_regression_artifacts(run_dir / "run.json")[1]
        return run_dir, run_result, regression_report

    for run_dir, run_result in runs:
        if run_result["run_id"] == run_id:
            regression_report = load_run_and_regression_artifacts(run_dir / "run.json")[1]
            return run_dir, run_result, regression_report

    raise ViewError(f"Run not found under {output_root}: {run_id}")


def _failed_items(regression_report: RegressionReport) -> list[dict[str, str]]:
    return [
        {
            "case_id": item["case_id"],
            "check": item["check"],
            "expected": item["expected"],
            "actual": item["actual"],
            "reason": item.get("reason", item["message"]),
        }
        for item in regression_report["regressions"]
    ]


def _read_run_result(path: Path) -> RunResult:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_trace(path: Path) -> StoredTrace:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_expectation(name: str, value: object) -> str:
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            if name == "critical_tool_sequence":
                return " -> ".join(value)
            return ", ".join(value)
        return json.dumps(value)
    return str(value)
