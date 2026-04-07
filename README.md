# AgentCI

CI guardrails for tool-using AI agents.

This repository is the Day 3-5 refocus for AgentCI: a narrow PR-time regression harness for internal workflow agents. The goal is to prove one end-to-end slice: load one config, run one adapter against one sample case, produce a pass or fail result, and surface that clearly in GitHub Actions.

## Why this repo exists

This scaffold is intentionally small:
- one Python CLI
- one command-based adapter contract
- one deterministic eval engine
- repo-local JSON artifacts
- one draft GitHub Actions workflow

It is not a full platform, dashboard, or framework integration layer.

## Current scope

The v1 wedge is **internal workflow agents** such as:
- ticket triage agents
- follow-up task agents
- internal ops workflow agents
- CRM update agents

The initial blocking checks are:
- required tools used
- forbidden tools not used
- critical tool order respected
- output contains expected facts

## Repository layout

```text
src/agentci/          Python package for the CLI and core runtime
agentci/tests/        Sample repo-local regression cases
scripts/              Sample adapter command implementation
.github/workflows/    Draft PR workflow
docs/                 Supporting docs for setup and workflow behavior
```

## Quick start

Install the package in editable mode:

```bash
python -m pip install -e .
```

Run the sample suite:

```bash
agentci run --config agentci.yaml
```

Run the intentional regression fixture:

```bash
agentci run --config tests/fixtures/regression-agentci.yaml
```

## Current command status

- `agentci run` is minimally implemented for the scaffold and should work end-to-end with the sample adapter.
- `agentci report` is optional convenience for local inspection and is not part of the critical CI path.
- `agentci init` and `agentci compare` exist as CLI placeholders with TODOs so the interface is visible early.

## Exit code semantics

- `0` means no blocking regressions were found.
- `1` means AgentCI detected a product behavior regression.
- `2` means AgentCI hit a config, adapter, tooling, or runtime failure. This is a harness failure, not evidence that the product behavior regressed.

## Adapter contract

The adapter is a simple command:
- AgentCI sends one test case JSON object to `stdin`
- the adapter writes one JSON object to `stdout`

Expected adapter output:

```json
{
  "final_output": "OPS-42 is Blocked. Created follow-up OPS-99 for the Safari checkout issue.",
  "trace": {
    "case_id": "create-followup-ticket",
    "events": []
  }
}
```

## Why the scaffold avoids extra dependencies

This initial repo uses only the Python standard library. The config file is still named `agentci.yaml`, but the parser only supports the small subset of YAML the MVP needs today. That keeps local setup and CI installation trivial while the interface is still settling.

## Important TODOs

- flesh out `agentci init`
- implement `agentci compare`
- harden config validation
- expand trace normalization
- add more unit tests
- refine the PR comment workflow
