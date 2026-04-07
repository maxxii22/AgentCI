"""Render the compact AgentCI PR comment from saved artifacts.

Why this file exists:
It gives GitHub Actions and local debugging the same tiny, deterministic path
for producing reviewer-facing markdown without adding a new product surface.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agentci.reporter import (  # noqa: E402
    find_latest_run_json,
    load_run_and_regression_artifacts,
    render_missing_artifact_comment,
    render_pr_comment,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render AgentCI PR comment markdown")
    parser.add_argument("--runs-root", default=".agentci/runs")
    parser.add_argument("--run")
    parser.add_argument("--regressions")
    parser.add_argument("--output")
    parser.add_argument("--exit-code", default="unknown")
    parser.add_argument("--run-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    run_path = Path(args.run).resolve() if args.run else find_latest_run_json(Path(args.runs_root).resolve())
    if run_path is None:
        rendered = render_missing_artifact_comment(args.exit_code, args.run_url)
    else:
        regression_path = Path(args.regressions).resolve() if args.regressions else None
        run_result, regression_report = load_run_and_regression_artifacts(run_path, regression_path)
        rendered = render_pr_comment(
            run_result,
            regression_report,
            exit_code=args.exit_code,
            run_url=args.run_url,
        )

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
