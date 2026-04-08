"""Human-readable summaries for local runs, CI, and PR comments.

Why this file exists:
It keeps console and markdown rendering out of the runner so report formatting
can evolve without changing execution behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentci.schemas import RegressionItem, RegressionReport, RunResult


def infer_exit_code(run_result: RunResult) -> int:
    """Infer the stable CLI exit code from the run artifact."""

    result_kind = str(run_result.get("result_kind", "pass"))
    if result_kind == "runtime_failure":
        return 2
    if result_kind == "regression":
        return 1
    return 0


def render_text_summary(run_result: RunResult) -> str:
    """Render a short text summary for local CLI usage."""

    summary = run_result["summary"]
    failed_details = _failed_case_details_from_run(run_result)
    lines = [
        "AgentCI run summary",
        f"outcome: {run_result.get('result_kind', 'pass')}",
        f"run_id: {run_result['run_id']}",
        f"status: {run_result['status']}",
        f"cases: {summary['total']} total, {summary['passed']} passed, {summary['failed']} failed",
    ]

    if "error" in run_result:
        error = run_result["error"]
        lines.append(f"error_stage: {error['stage']}")
        lines.append(f"error_message: {error['message']}")

    if failed_details:
        lines.append("failed cases:")
        for detail in failed_details:
            lines.append(
                f"- {detail['case_id']} | check={detail['check']} | expected={detail['expected']} | "
                f"actual={detail['actual']} | reason={detail['reason']}"
            )

    return "\n".join(lines)


def render_markdown_report(run_result: RunResult, regression_report: RegressionReport) -> str:
    """Render a markdown report suitable for a PR comment or job summary."""

    return render_pr_comment(
        run_result,
        regression_report,
        exit_code=infer_exit_code(run_result),
    )


def render_pr_comment(
    run_result: RunResult,
    regression_report: RegressionReport,
    *,
    exit_code: int | str,
    run_url: str | None = None,
) -> str:
    """Render the compact markdown comment used for PRs and job summaries."""

    summary = run_result["summary"]
    failed_case_ids = list(
        regression_report.get("failed_case_ids")
        or [case["case_id"] for case in run_result["cases"] if case["status"] == "failed"]
    )
    failed_details = _failed_case_details(run_result, regression_report)
    heading, meaning = _describe_outcome(str(run_result.get("result_kind", "pass")), str(exit_code))
    lines = [
        f"## AgentCI: {heading}",
        "",
        meaning,
        "",
        f"- Exit code: `{exit_code}`",
        f"- Run ID: `{run_result['run_id']}`",
        f"- Cases: **{summary['total']}** total, **{summary['passed']}** passed, **{summary['failed']}** failed",
    ]

    if failed_case_ids:
        lines.append(
            "- Failed case IDs: " + ", ".join(f"`{case_id}`" for case_id in failed_case_ids)
        )

    if run_url:
        lines.append(f"- Artifacts and logs: [GitHub Actions run]({run_url})")
    else:
        lines.append("- Artifacts and logs: see workflow artifacts for this run.")

    lines.append("")

    if "error" in run_result:
        error = run_result["error"]
        lines.extend(
            [
                "### AgentCI runtime failure",
                "",
                f"- Stage: `{error['stage']}`",
                f"- Message: {error['message']}",
                "- Meaning: AgentCI could not complete the run. This is not evidence that product behavior regressed.",
                "",
            ]
        )
    elif failed_details:
        lines.append("### Failed cases")
        lines.append("")
        for detail in failed_details:
            lines.append(f"- `{detail['case_id']}`")
            lines.append(f"  failed check: `{detail['check']}`")
            lines.append(f"  expected: `{detail['expected']}`")
            lines.append(f"  actual: `{detail['actual']}`")
            lines.append(f"  reason: {detail['reason']}")
            lines.append("")
    else:
        lines.append("No blocking regressions found.")

    return "\n".join(lines)


def render_ci_summary(
    run_result: RunResult,
    regression_report: RegressionReport,
    *,
    exit_code: int | str,
) -> str:
    """Backwards-compatible wrapper for the PR comment/job summary renderer."""

    return render_pr_comment(
        run_result,
        regression_report,
        exit_code=exit_code,
    )


def load_run_and_regression_artifacts(
    run_path: Path,
    regression_path: Path | None = None,
) -> tuple[RunResult, RegressionReport]:
    """Load the saved run and regression artifacts used for summaries."""

    run_result = _read_json(run_path)
    effective_regression_path = regression_path or run_path.parent / "regression-report.json"
    if effective_regression_path.exists():
        regression_report = _read_json(effective_regression_path)
    else:
        regression_report = _build_default_regression_report(run_result)
    return run_result, regression_report


def render_missing_artifact_comment(exit_code: int | str, run_url: str | None = None) -> str:
    """Render a fallback comment when AgentCI did not produce a run artifact."""

    lines = [
        "## AgentCI: Runtime/tooling failure",
        "",
        "AgentCI did not produce a run artifact. This is a harness failure, not proof of product regression.",
        "",
        f"- Exit code: `{exit_code}`",
    ]
    if run_url:
        lines.append(f"- Artifacts and logs: [GitHub Actions run]({run_url})")
    else:
        lines.append("- Artifacts and logs: see workflow logs for this run.")
    return "\n".join(lines)


def find_latest_run_json(runs_root: Path) -> Path | None:
    """Find the most recent run.json beneath a run output root."""

    run_files = sorted(runs_root.glob("**/run.json"))
    if not run_files:
        return None
    return run_files[-1]


def _read_json(path: Path) -> RunResult | RegressionReport:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_default_regression_report(run_result: RunResult) -> RegressionReport:
    summary = run_result["summary"]
    return {
        "run_id": run_result["run_id"],
        "baseline_source": "repo_test_expectations",
        "result_kind": str(run_result.get("result_kind", "pass")),
        "status": "failed" if summary["failed"] else "passed",
        "failed_case_ids": [case["case_id"] for case in run_result["cases"] if case["status"] == "failed"],
        "summary": {
            "total_cases": summary["total"],
            "passed_cases": summary["passed"],
            "failed_cases": summary["failed"],
            "blocking_regressions": 0,
            "non_blocking_warnings": 0,
        },
        "regressions": [],
    }


def _failed_case_details(
    run_result: RunResult, regression_report: RegressionReport
) -> list[dict[str, str]]:
    if regression_report["regressions"]:
        return [
            {
                "case_id": regression["case_id"],
                "check": regression["check"],
                "expected": regression["expected"],
                "actual": regression["actual"],
                "reason": regression.get("reason", regression["message"]),
            }
            for regression in regression_report["regressions"]
        ]
    return _failed_case_details_from_run(run_result)


def _failed_case_details_from_run(run_result: RunResult) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for case in run_result["cases"]:
        if case["status"] != "failed":
            continue
        for check in case["checks"]:
            if check["status"] != "failed":
                continue
            details.append(
                {
                    "case_id": case["case_id"],
                    "check": check["name"],
                    "expected": str(check.get("expected", "")),
                    "actual": str(check.get("actual", "")),
                    "reason": str(check.get("reason", check.get("message", "check failed"))),
                }
            )
    return details


def _describe_outcome(result_kind: str, exit_code: str) -> tuple[str, str]:
    if result_kind == "regression":
        return (
            "Regression detected",
            "AgentCI completed the run and found a blocking agent behavior regression.",
        )
    if result_kind == "runtime_failure":
        return (
            "Runtime/tooling failure",
            "AgentCI hit a config, loader, adapter, tooling, or runtime failure. This is not evidence that product behavior regressed.",
        )
    return (
        "Pass",
        "AgentCI completed the run and found no blocking regressions.",
    )
