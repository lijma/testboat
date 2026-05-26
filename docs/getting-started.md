# Getting Started

## Install

```bash
pip install ftest
```

## Initialize Workspace

```bash
cd your-project
ftest init
```

Creates `.ftest/draft/` with the standard directory structure and sets the active version to `draft`.

## Enable Your AI Agent

```bash
ftest enable claude      # Claude Code
ftest enable copilot     # GitHub Copilot
ftest enable cursor      # Cursor
ftest enable kiro        # Kiro
ftest enable list        # see all supported agents
```

This creates agent-specific instruction files so your AI automatically follows the ftest workflow.

## Create a Test Strategy

```bash
ftest strategy create
```

Edit `.ftest/draft/strategy.yaml` — fill in scope, risk matrix, entry/exit criteria — then validate:

```bash
ftest strategy validate
```

## Add Test Cases

```bash
# Register tags first
ftest tag add sprint v1.0
ftest tag add type functional
ftest tag add module auth

# Create a test case (AI fills in the steps)
ftest case add --title "Login with wrong password returns 401" \
               --sprint v1.0 --type functional --module auth --req-id STORY-001
```

Then ask your AI agent to fill in `steps`, `preconditions`, and `expected_result` in the generated YAML file.

## Execute and Record Results

```bash
# Create execution plan
ftest plan create TC-001 --type automated --tool pytest

# Register automation script
ftest plan register TC-001 .ftest/draft/executions/automate/pytest/tests/test_TC001.py
ftest plan status TC-001 approved

# Record result (AI runs the script and records)
ftest result record TC-001 pass --type automated --by "AI"
```

## Validate Before Reporting

```bash
ftest validate
```

Checks: format integrity · requirements coverage · execution completeness · exit criteria.

## Generate Reports

```bash
ftest report strategy   # test strategy HTML
ftest report sprint     # sprint test report (cases + results + bugs)
ftest report closure    # closure report with sign-off status
ftest preview           # open in browser on a random local port
```

## Manage Versions

```bash
ftest version create v1.0          # snapshot draft as v1.0
ftest version create v1.1 v1.0     # create v1.1 based on v1.0
ftest version switch v1.0          # all commands now operate on v1.0
ftest version active               # show current active version
ftest version list                 # list all versions
```
