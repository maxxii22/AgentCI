"""Artifact writing for AgentCI runs.

Why this file exists:
It centralizes JSON output so the runner can stay focused on execution and the
artifact layout stays stable for CI and local debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def prepare_run_directory(output_root: Path, run_id: str) -> Path:
    """Create the run directory and its trace subdirectory."""

    run_dir = output_root / run_id
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)
    return run_dir


def write_trace(run_dir: Path, case_id: str, trace: dict[str, Any]) -> str:
    """Write one normalized trace file and return a run-relative path."""

    trace_path = run_dir / "traces" / f"{case_id}.json"
    _write_json(trace_path, trace)
    return trace_path.relative_to(run_dir).as_posix()


def write_artifact(run_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    """Write one top-level run artifact file."""

    path = run_dir / filename
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
