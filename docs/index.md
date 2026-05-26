# ftest

**Manage tests like code — CLI + AI agent skill for the complete testing lifecycle.**

## What is ftest?

ftest treats test artifacts (strategy, test cases, execution results, bugs, reports) as structured files in a versioned directory — just like source code. AI agents and CLI tools operate on the same files, ensuring a single source of truth across the entire testing lifecycle.

## Core Idea

```
.ftest/
  draft/              ← always the active working version
    strategy.yaml     ← risk-based test strategy
    cases/            ← TC-001.yaml, TC-002.yaml, ...
    bugs/             ← BUG-001.yaml, ...
    executions/       ← plans, results, automation scripts
    reports/          ← generated HTML reports
```

**CLI** enforces consistency and state machines.  
**AI agent** generates content, executes automation, and communicates progress.

## Why ftest?

- **Structured**: every artifact is YAML — diffable, reviewable, version-controlled
- **AI-native**: agent skills guide AI through the full SOP automatically
- **Iterative**: event-driven — any user input (comment, new req, manual result) triggers the right update
- **Multi-version**: snapshot any moment as a named version (`v1.0`, `v1.1`)

[Get started →](getting-started.md){ .md-button .md-button--primary }
[View commands →](commands.md){ .md-button }
