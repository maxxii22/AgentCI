"""Human-readable summaries for local runs and CI.

Why this file exists:
It keeps console and markdown rendering out of the runner so report formatting
can evolve without changing execution behavior.
"""

from __future__ import annotations

from agentci.schemas import RegressionReport, RunResult


def render_text_summary(run_result: RunResult) -> str:
    """Render a short text summary for local CLI usage."""

    summary = run_result["summary"]
    lines = [
        "AgentCI run summary",
        f"run_id: {run_result['run_id']}",
        f"status: {run_result['status']}",
        f"cases: {summary['total']} total, {summary['passed']} passed, {summary['failed']} failed",
    ]

    if "error" in run_result:
        error = run_result["error"]
        lines.append(f"error_stage: {error['stage']}")
        lines.append(f"error_message: {error['message']}")

    failed_cases = [case for case in run_result["cases"] if case["status"] == "failed"]
    if failed_cases:
        lines.append("failed cases:")
        for case in failed_cases:
            lines.append(f"- {case['case_id']}")

    return "\n".join(lines)


def render_markdown_report(run_result: RunResult, regression_report: RegressionReport) -> str:
    """Render a markdown report suitable for a PR comment or job summary."""

    summary = run_result["summary"]
    lines = [
        "## AgentCI",
        "",
        f"- Status: **{run_result['status']}**",
        f"- Cases: **{summary['total']}** total, **{summary['passed']}** passed, **{summary['failed']}** failed",
        f"- Run ID: `{run_result['run_id']}`",
        "",
    ]

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

    if regression_report["regressions"]:
        lines.append("### Blocking regressions")
        lines.append("")
        for regression in regression_report["regressions"]:
            lines.append(
                f"- `{regression['case_id']}` failed `{regression['check']}`: {regression['message']}"
            )
        lines.append("")
    else:
        lines.append("No blocking regressions found.")
        lines.append("")

    lines.append("### Per-case results")
    lines.append("")
    for case in run_result["cases"]:
        lines.append(f"- `{case['case_id']}`: **{case['status']}**")

    return "\n".join(lines)
