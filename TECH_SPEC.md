# Technical Spec

## Why this file exists

This file locks the minimum viable technical shape for the AgentCI Day 3-5 refocus so implementation stays narrow and shippable.

## Goal

Ship a believable MVP in 14 days that lets a developer:
1. add `agentci.yaml`
2. define JSON test cases
3. run `agentci run` locally
4. run the same suite in GitHub Actions on every PR
5. fail the PR when deterministic behavior regresses

## Required components

### CLI
- thin Python entrypoint
- owns argument parsing and exit codes
- keeps orchestration logic shallow
- treats `run` as the only essential MVP command and `report` as an optional local helper

### Config loader
- reads `agentci.yaml`
- validates the small v1 schema
- resolves adapter command, test glob, and output directory

### Test case loader
- loads committed JSON files
- validates required top-level fields
- keeps schemas human-editable

### Command adapter runner
- sends one case JSON payload to `stdin`
- reads one result JSON payload from `stdout`
- treats non-zero adapter exit as runtime error

### Eval engine
- deterministic only
- blocking checks:
  - required tools
  - forbidden tools
  - critical tool sequence
  - expected output facts

### Artifact store
- writes local JSON files only
- output files:
  - `run.json`
  - `regression-report.json`
  - `traces/*.json`

### GitHub Actions workflow
- runs on pull requests
- uploads artifacts
- posts a PR comment summary generated directly from run artifacts
- fails when the CLI exits non-zero

## Adapter contract

Input:
- one test case JSON document on `stdin`

Output:

```json
{
  "final_output": "string",
  "trace": {
    "case_id": "string",
    "events": []
  }
}
```

## CLI exit codes

- `0`: success, no blocking regressions
- `1`: product behavior regression found
- `2`: AgentCI config, adapter, tooling, or runtime failure; this is not evidence that product behavior regressed

## Key implementation choices

- language: Python
- dependencies: standard library only
- config format: narrow YAML subset
- storage: local JSON artifacts
- tools: mocked fixtures only
- framework support: one command adapter abstraction

## Immediate TODOs

- make `init` write starter files
- implement run-to-run compare flow
- harden malformed trace handling
- make the PR comment updater more robust
