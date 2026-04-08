# AgentCI

CI/CD for AI agents. AgentCI tests agent behavior in pull requests and blocks broken merges before they ship.

## Problem

AI agents break silently.

- A prompt change can break tool usage
- An agent can call the wrong tool
- Output quality can degrade without throwing an error
- Teams often find out after merge or in production

## Solution

AgentCI puts behavior checks in CI.

On every pull request, it can:
- run agent test cases
- validate required and forbidden tools
- catch behavioral regressions
- fail the check before bad agent changes merge

## Example output

```text
❌ Regression detected

- Missing required tool: slack.send_message
- Cases: 3 total, 2 passed, 1 failed

This PR will be blocked until fixed.
```

## How it works

1. Define a few agent test cases
2. Run `agentci run`
3. Add AgentCI to GitHub Actions so PRs fail on regressions

## Quickstart

```bash
git clone https://github.com/maxxii22/AgentCI.git
cd AgentCI
python -m pip install -e .
agentci run --config agentci.yaml
```

## What AgentCI tests

- required tools
- forbidden tools
- tool call order
- expected output signals
- agent behavior, not just code paths

## Why it matters

- AI agents are harder to trust than normal code
- unit tests usually miss behavior regressions
- CI should verify what the agent actually does
- AgentCI gives reviewers a clear pass/fail signal inside the PR

## Status

Early-stage MVP.

Today, AgentCI supports:
- deterministic regression checks
- local runs
- GitHub Actions PR checks
- PR comments with failure explanations
- trace artifacts for debugging

## Try AgentCI

If you are building tool-using agents, try the repo and open an issue or reach out.

If you want help setting it up on a real agent workflow, I can help you get the first PR check running quickly.
