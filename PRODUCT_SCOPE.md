# Product Scope

## Product definition

AgentCI is a PR-time regression harness for tool-using agents that runs deterministic agent tests in CI and blocks merges when tool behavior regresses.

## Target user

The initial user is an AI engineer or platform engineer shipping an internal workflow agent from a GitHub repo.

## Problem solved

Tool-using agents regress in subtle ways that unit tests miss:
- they stop calling a required tool
- they call tools in the wrong order
- they skip critical workflow steps
- they omit key facts from the final output

AgentCI is meant to catch those regressions in pull requests, before merge.

## Chosen wedge

The initial wedge is **internal workflow agents**.

Why this wedge:
- easiest to test deterministically with mocked tools
- painful failures show up quickly in real workflows
- small enough technical surface for a 14-day MVP
- clean path to future expansion later

## In-scope MVP

- root `agentci.yaml`
- committed JSON test cases
- command-based adapter interface
- mocked tool fixtures
- deterministic eval checks
- local CLI
- JSON run artifacts
- GitHub Actions integration

## Explicitly out of scope

- hosted dashboard
- remote storage or control plane
- enterprise governance
- real external tool execution in CI
- framework-specific SDKs
- multi-agent flows
- latency or cost merge blockers
- LLM judge scoring

## First 30-day success

The first version is successful if:
- 3 pilot repos adopt it
- setup time stays under 30 minutes
- pilots commit at least 20 regression cases total
- AgentCI catches at least 5 real regressions before merge
- flaky blocking failures stay under 5%
