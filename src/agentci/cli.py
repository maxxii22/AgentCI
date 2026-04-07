"""Command-line entrypoint for AgentCI.

Why this file exists:
It exposes the narrow CLI surface for the MVP while keeping heavy logic in
other modules so each part stays easy to change.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentci.config import ConfigError, load_config
from agentci.reporter import render_markdown_report, render_text_summary
from agentci.runner import execute_run, write_error_run


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(prog="agentci", description="AgentCI CLI scaffold")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Scaffold starter files (TODO)")
    init_parser.add_argument("--path", default=".")
    init_parser.add_argument("--example", default="internal-workflow")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=command_init)

    run_parser = subparsers.add_parser("run", help="Run the configured regression suite")
    run_parser.add_argument("--config", default="agentci.yaml")
    run_parser.add_argument("--case")
    run_parser.add_argument("--output-dir")
    run_parser.add_argument("--format", default="text", choices=["text", "json", "github"])
    run_parser.add_argument("--fail-on", default="blocking", choices=["blocking", "never"])
    run_parser.set_defaults(func=command_run)

    compare_parser = subparsers.add_parser("compare", help="Compare two run artifacts (TODO)")
    compare_parser.add_argument("--base", required=True)
    compare_parser.add_argument("--head", required=True)
    compare_parser.add_argument("--format", default="text", choices=["text", "json", "markdown"])
    compare_parser.add_argument("--fail-on", default="regression", choices=["regression", "never"])
    compare_parser.set_defaults(func=command_compare)

    report_parser = subparsers.add_parser(
        "report", help="Optional helper to render a saved run into text or markdown"
    )
    report_parser.add_argument("--input", required=True, help="Path to a run.json artifact")
    report_parser.add_argument("--regressions", help="Optional path to regression-report.json")
    report_parser.add_argument(
        "--format", default="text", choices=["text", "markdown", "github-summary"]
    )
    report_parser.add_argument("--output")
    report_parser.set_defaults(func=command_report)

    return parser


def command_init(args: argparse.Namespace) -> int:
    """Placeholder for the future file scaffolding command."""

    print(
        "TODO: `agentci init` is not implemented yet. "
        "The repo already contains a starter scaffold you can copy from."
    )
    return 0


def command_run(args: argparse.Namespace) -> int:
    """Run the configured test suite and emit artifacts."""

    output_root = _resolve_fallback_output_root(args.output_dir)

    try:
        config = load_config(args.config)
        output_root = _resolve_output_root_for_cli(config.root_dir, args.output_dir, config.output_dir)
        run_result, regression_report, run_dir = execute_run(
            config,
            case_id=args.case,
            output_dir_override=args.output_dir,
        )
    except ConfigError as error:
        run_result, regression_report, run_dir = write_error_run(
            output_root,
            stage="config",
            message=str(error),
        )
        print(f"AgentCI error: {error}", file=sys.stderr)
    except Exception as error:  # pragma: no cover - defensive fallback for the scaffold
        run_result, regression_report, run_dir = write_error_run(
            output_root,
            stage="runtime",
            message=str(error),
        )
        print(f"AgentCI unexpected error: {error}", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(run_result, indent=2))
    else:
        print(render_text_summary(run_result))
        print(f"result_kind: {_result_kind(run_result, regression_report)}")
        print(f"artifacts: {run_dir}")

    if args.fail_on == "never":
        return 0
    if run_result["status"] == "error":
        return 2
    if regression_report["status"] == "failed":
        return 1
    return 0


def command_compare(args: argparse.Namespace) -> int:
    """Placeholder for the future run-to-run compare flow."""

    print(
        "TODO: `agentci compare` is not implemented yet. "
        "Use saved run artifacts directly for now."
    )
    return 0


def command_report(args: argparse.Namespace) -> int:
    """Render a saved run artifact into text or markdown."""

    run_path = Path(args.input).resolve()
    if not run_path.exists():
        print(f"AgentCI error: run artifact not found: {run_path}", file=sys.stderr)
        return 2

    regression_path = (
        Path(args.regressions).resolve()
        if args.regressions
        else run_path.parent / "regression-report.json"
    )

    run_result = _read_json(run_path)
    regression_report = _read_json(regression_path) if regression_path.exists() else {
        "run_id": run_result["run_id"],
        "baseline_source": "repo_test_expectations",
        "status": "passed",
        "summary": {"blocking_regressions": 0, "non_blocking_warnings": 0},
        "regressions": [],
    }

    if args.format in {"markdown", "github-summary"}:
        rendered = render_markdown_report(run_result, regression_report)
    else:
        rendered = render_text_summary(run_result)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 0


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_fallback_output_root(output_dir: str | None) -> Path:
    if output_dir:
        override = Path(output_dir)
        if override.is_absolute():
            return override
        return (Path.cwd() / override).resolve()
    return (Path.cwd() / ".agentci" / "runs").resolve()


def _resolve_output_root_for_cli(
    root_dir: Path, output_dir_override: str | None, config_output_dir: Path
) -> Path:
    if output_dir_override:
        override = Path(output_dir_override)
        if override.is_absolute():
            return override
        return (root_dir / override).resolve()
    return config_output_dir


def _result_kind(
    run_result: dict[str, object], regression_report: dict[str, object]
) -> str:
    if run_result.get("status") == "error":
        return "runtime_failure"
    if regression_report.get("status") == "failed":
        return "regression"
    return "pass"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the console script and `python -m`."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
