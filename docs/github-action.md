# GitHub Action Draft

## Why this file exists

This note explains the intent behind the draft workflow under `.github/workflows/agentci.yml` so the first coding sessions do not overbuild CI behavior.

## Intended behavior

On every pull request:
1. checkout the repo
2. install the local AgentCI package
3. run `agentci run`
4. build a markdown summary directly from `run.json` and `regression-report.json`
5. upload JSON artifacts
6. post or update a single PR comment
7. fail the check if regressions or runtime errors occurred

## Current limitations

- the workflow is still a draft
- the PR comment updater is intentionally simple
- the run command is still using local JSON artifacts only
- compare-to-main behavior is not implemented yet
- exit code `2` means AgentCI hit a config, adapter, tooling, or runtime failure, not that the product definitely regressed
