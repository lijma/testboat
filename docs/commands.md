# Commands Reference

## Workspace

| Command | Description |
|---------|-------------|
| `testboat init [dir]` | Initialize `.testboat/` workspace (idempotent) |
| `testboat enable <agent>` | Create agent rules + skill files |
| `testboat enable list` | Show all supported agents |

## Version Management

| Command | Description |
|---------|-------------|
| `testboat version create <v> [base]` | Snapshot draft (or base version) as named version |
| `testboat version switch <v>` | Set active version (all commands operate here) |
| `testboat version active` | Show currently active version |
| `testboat version list` | List all named versions |
| `testboat version show <v>` | Show version details |

## Strategy

| Command | Description |
|---------|-------------|
| `testboat strategy create` | Generate `strategy.yaml` template |
| `testboat strategy validate` | Validate schema (required before reporting) |

## Tags

| Command | Description |
|---------|-------------|
| `testboat tag add <kind> <value>` | Register a tag (`sprint` / `type` / `module`) |
| `testboat tag list` | Show all registered tags |

## Test Cases

| Command | Description |
|---------|-------------|
| `testboat case add --title "..." [--sprint] [--type] [--module] [--req-id]` | Create TC metadata skeleton |
| `testboat case list [--sprint] [--type] [--module] [--status]` | List test cases |
| `testboat case show <id>` | Show full TC details |
| `testboat case status <id> <status>` | Transition status (`draft→ready→pass/fail/blocked`) |
| `testboat case validate <id\|all> [--sprint] [--module]` | Validate schema + tag references |

## Execution Plans

| Command | Description |
|---------|-------------|
| `testboat plan create <id> [--type] [--tool]` | Create execution plan for a TC |
| `testboat plan register <id> <script>` | Link automation script to plan |
| `testboat plan status <id> <status>` | Update plan status (`draft→approved`) |
| `testboat plan list [--type] [--status]` | List plans |
| `testboat plan show <id>` | Show plan details |

## Execution Results

| Command | Description |
|---------|-------------|
| `testboat result record <tc> <status> [--type] [--by] [--notes]` | Record one execution result |
| `testboat result list [--tc]` | List results |
| `testboat result show <id>` | Show result details |
| `testboat matrix show [tc]` | Global execution tracking matrix |

## Bugs

| Command | Description |
|---------|-------------|
| `testboat bug add --title "..." [--severity] [--priority] [--tc] [--sprint] [--module]` | File a bug |
| `testboat bug list [--status] [--priority] [--severity] [--sprint] [--module]` | List bugs |
| `testboat bug show <id>` | Show bug details |
| `testboat bug status <id> <status>` | Transition bug status |

Bug status machine: `new → triaged → in-progress → fixed → pending-retest → verified → closed`

## Validation

| Command | Description |
|---------|-------------|
| `testboat validate` | Run all 4 pre-report checks |

Checks: ① Format validation · ② Requirements coverage · ③ Execution completeness · ④ Exit criteria

## Reports & Preview

| Command | Description |
|---------|-------------|
| `testboat report strategy` | Generate strategy HTML |
| `testboat report sprint` | Generate sprint test report |
| `testboat report closure [--summary "..."]` | Generate closure report |
| `testboat preview` | Serve reports locally (kills previous server) |
| `testboat preview --pdf <html>` | Export HTML report to PDF |
