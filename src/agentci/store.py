"""Artifact writing for AgentCI runs.

Why this file exists:
It centralizes JSON output so the runner can stay focused on execution and the
artifact layout stays stable for CI and local debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from agentci.schemas import (
    AdapterOutput,
    CaseResult,
    RegressionItem,
    StoredTrace,
    TestCase,
    Trace,
    TraceToolStep,
)


def prepare_run_directory(output_root: Path, run_id: str) -> Path:
    """Create the run directory and its trace subdirectory."""

    run_dir = output_root / run_id
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)
    return run_dir


def build_trace_artifact(
    case: TestCase,
    adapter_output: AdapterOutput,
    case_result: CaseResult,
    regressions: list[RegressionItem],
) -> StoredTrace:
    """Build the human-friendly per-case trace artifact."""

    raw_trace = adapter_output["trace"]
    actual_tools_used = _extract_tool_names(raw_trace)
    failed_checks = [
        {
            "check": check["name"],
            "expected": str(check.get("expected", "")),
            "actual": str(check.get("actual", "")),
            "reason": str(check.get("reason", check.get("message", "check failed"))),
        }
        for check in case_result["checks"]
        if check["status"] == "failed"
    ]
    evaluation_summary = (
        "All blocking checks passed."
        if case_result["status"] == "passed"
        else f"{len(failed_checks)} blocking check(s) failed."
    )

    trace_artifact: StoredTrace = {
        "case_id": case["id"],
        "case_name": case["name"],
        "prompt": _extract_prompt(case),
        "input": case["input"],
        "expectations": case.get("expect", {}),
        "actual_final_output": adapter_output["final_output"],
        "actual_tools_used": actual_tools_used,
        "tool_timeline": _build_tool_timeline(actual_tools_used),
        "evaluation": {
            "status": case_result["status"],
            "summary": evaluation_summary,
            "failed_checks": failed_checks,
        },
        "raw_trace": raw_trace,
    }
    if regressions:
        trace_artifact["failure_reason"] = " ".join(regression["reason"] for regression in regressions)
    return trace_artifact


def write_trace(run_dir: Path, case_id: str, trace: StoredTrace) -> str:
    """Write one normalized trace file and return a run-relative path."""

    trace_path = run_dir / "traces" / f"{case_id}.json"
    _write_json(trace_path, trace)
    return trace_path.relative_to(run_dir).as_posix()


def write_artifact(run_dir: Path, filename: str, payload: Mapping[str, Any]) -> Path:
    """Write one top-level run artifact file."""

    path = run_dir / filename
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _extract_prompt(case: TestCase) -> str:
    messages = case["input"].get("messages")
    if not isinstance(messages, list):
        return ""
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _extract_tool_names(trace: Trace) -> list[str]:
    return [
        str(event.get("tool_name", ""))
        for event in trace.get("events", [])
        if event.get("type") == "tool_call" and event.get("tool_name")
    ]


def _build_tool_timeline(tool_names: list[str]) -> list[TraceToolStep]:
    return [
        {"step": index, "tool_name": tool_name}
        for index, tool_name in enumerate(tool_names, start=1)
    ]
