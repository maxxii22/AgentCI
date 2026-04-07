"""Execution orchestration for the AgentCI Day 3-5 refocus.

Why this file exists:
It ties config loading, case loading, adapter execution, evals, and artifact
writing together while keeping the CLI layer very thin.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path

from agentci.adapters.command import AdapterError, run_command_adapter
from agentci.config import AgentCIConfig
from agentci.evals import build_regression_report, evaluate_case
from agentci.loader import LoaderError, load_test_cases
from agentci.schemas import RegressionReport, RunResult
from agentci.store import prepare_run_directory, write_artifact, write_trace


class RunError(RuntimeError):
    """Raised when the requested run cannot be executed."""


def execute_run(
    config: AgentCIConfig,
    *,
    case_id: str | None = None,
    output_dir_override: str | Path | None = None,
) -> tuple[RunResult, RegressionReport, Path]:
    """Execute the configured suite and write JSON artifacts to a run directory."""

    started_at = _utc_now()
    run_id = f"run_{started_at.replace(':', '-').replace('.', '-')}"

    output_root = _resolve_output_root(config, output_dir_override)
    run_dir = prepare_run_directory(output_root, run_id)

    case_results = []
    regressions = []

    try:
        cases = load_test_cases(config.root_dir, config.tests.glob)
        if case_id:
            cases = [case for case in cases if case["id"] == case_id]
            if not cases:
                raise RunError(f"No test case matched id: {case_id}")

        for case in cases:
            started = time.perf_counter()
            adapter_output = run_command_adapter(config.adapter.command, case, config.root_dir)
            case_result, case_regressions = evaluate_case(case, adapter_output)
            case_result["duration_ms"] = int((time.perf_counter() - started) * 1000)
            case_result["trace_path"] = write_trace(run_dir, case["id"], adapter_output["trace"])
            case_results.append(case_result)
            regressions.extend(case_regressions)
    except (AdapterError, LoaderError, RunError) as error:
        return _write_error_artifacts(
            run_dir,
            run_id=run_id,
            started_at=started_at,
            case_results=case_results,
            regressions=regressions,
            stage=_classify_error_stage(error),
            message=str(error),
        )

    finished_at = _utc_now()
    failed_count = sum(1 for case in case_results if case["status"] == "failed")
    passed_count = len(case_results) - failed_count

    run_result: RunResult = {
        "run_id": run_id,
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "result_kind": "regression" if failed_count else "pass",
        "status": "failed" if failed_count else "passed",
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": {
            "total": len(case_results),
            "passed": passed_count,
            "failed": failed_count,
        },
        "cases": case_results,
    }

    regression_report = build_regression_report(
        run_id=run_id,
        total_cases=len(case_results),
        passed_cases=passed_count,
        failed_cases=failed_count,
        regressions=regressions,
    )
    write_artifact(run_dir, "run.json", run_result)
    write_artifact(run_dir, "regression-report.json", regression_report)

    return run_result, regression_report, run_dir


def write_error_run(
    output_root: Path,
    *,
    stage: str,
    message: str,
) -> tuple[RunResult, RegressionReport, Path]:
    """Write error artifacts when the run fails before config-backed execution begins."""

    started_at = _utc_now()
    run_id = f"run_{started_at.replace(':', '-').replace('.', '-')}"
    run_dir = prepare_run_directory(output_root, run_id)
    return _write_error_artifacts(
        run_dir,
        run_id=run_id,
        started_at=started_at,
        case_results=[],
        regressions=[],
        stage=stage,
        message=message,
    )


def _resolve_output_root(
    config: AgentCIConfig, output_dir_override: str | Path | None
) -> Path:
    if output_dir_override is None:
        return config.output_dir

    override = Path(output_dir_override)
    if override.is_absolute():
        return override
    return (config.root_dir / override).resolve()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_error_artifacts(
    run_dir: Path,
    *,
    run_id: str,
    started_at: str,
    case_results: list[dict[str, object]],
    regressions: list[dict[str, str]],
    stage: str,
    message: str,
) -> tuple[RunResult, RegressionReport, Path]:
    finished_at = _utc_now()
    failed_count = sum(1 for case in case_results if case["status"] == "failed")
    passed_count = sum(1 for case in case_results if case["status"] == "passed")

    run_result: RunResult = {
        "run_id": run_id,
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "result_kind": "runtime_failure",
        "status": "error",
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": {
            "total": len(case_results),
            "passed": passed_count,
            "failed": failed_count,
        },
        "cases": case_results,
        "error": {
            "stage": stage,
            "message": message,
        },
    }

    regression_report: RegressionReport = {
        "run_id": run_id,
        "baseline_source": "repo_test_expectations",
        "result_kind": "runtime_failure",
        "status": "error",
        "failed_case_ids": sorted(
            {case["case_id"] for case in case_results if case["status"] == "failed"}
        ),
        "summary": {
            "total_cases": len(case_results),
            "passed_cases": passed_count,
            "failed_cases": failed_count,
            "blocking_regressions": len(regressions),
            "non_blocking_warnings": 0,
        },
        "regressions": regressions,
        "error": {
            "stage": stage,
            "message": message,
        },
    }

    write_artifact(run_dir, "run.json", run_result)
    write_artifact(run_dir, "regression-report.json", regression_report)

    return run_result, regression_report, run_dir


def _classify_error_stage(error: Exception) -> str:
    if isinstance(error, LoaderError):
        return "test_loader"
    if isinstance(error, AdapterError):
        return "adapter_runtime"
    if isinstance(error, RunError):
        return "run_setup"
    return "runtime"
