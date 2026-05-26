# Commands Reference

## Workspace

| Command | Description |
|---------|-------------|
| `ftest init [dir]` | Initialize `.ftest/` workspace (idempotent) |
| `ftest enable <agent>` | Create agent rules + skill files |
| `ftest enable list` | Show all supported agents |

## Version Management

| Command | Description |
|---------|-------------|
| `ftest version create <v> [base]` | Snapshot draft (or base version) as named version |
| `ftest version switch <v>` | Set active version (all commands operate here) |
| `ftest version active` | Show currently active version |
| `ftest version list` | List all named versions |
| `ftest version show <v>` | Show version details |

## Strategy

| Command | Description |
|---------|-------------|
| `ftest strategy create` | Generate `strategy.yaml` template |
| `ftest strategy validate` | Validate schema (required before reporting) |

## Tags

| Command | Description |
|---------|-------------|
| `ftest tag add <kind> <value>` | Register a tag (`sprint` / `type` / `module`) |
| `ftest tag list` | Show all registered tags |

## Test Cases

| Command | Description |
|---------|-------------|
| `ftest case add --title "..." [--sprint] [--type] [--module] [--req-id]` | Create TC metadata skeleton |
| `ftest case list [--sprint] [--type] [--module] [--status]` | List test cases |
| `ftest case show <id>` | Show full TC details |
| `ftest case status <id> <status>` | Transition status (`draft→ready→pass/fail/blocked`) |
| `ftest case validate <id\|all> [--sprint] [--module]` | Validate schema + tag references |

## Execution Plans

| Command | Description |
|---------|-------------|
| `ftest plan create <id> [--type] [--tool]` | Create execution plan for a TC |
| `ftest plan register <id> <script>` | Link automation script to plan |
| `ftest plan status <id> <status>` | Update plan status (`draft→approved`) |
| `ftest plan list [--type] [--status]` | List plans |
| `ftest plan show <id>` | Show plan details |

## Execution Results

| Command | Description |
|---------|-------------|
| `ftest result record <tc> <status> [--type] [--by] [--notes]` | Record one execution result |
| `ftest result list [--tc]` | List results |
| `ftest result show <id>` | Show result details |
| `ftest matrix show [tc]` | Global execution tracking matrix |

## Bugs

| Command | Description |
|---------|-------------|
| `ftest bug add --title "..." [--severity] [--priority] [--tc] [--sprint] [--module]` | File a bug |
| `ftest bug list [--status] [--priority] [--severity] [--sprint] [--module]` | List bugs |
| `ftest bug show <id>` | Show bug details |
| `ftest bug status <id> <status>` | Transition bug status |

Bug status machine: `new → triaged → in-progress → fixed → pending-retest → verified → closed`

## Validation

| Command | Description |
|---------|-------------|
| `ftest validate` | Run all 4 pre-report checks |

Checks: ① Format validation · ② Requirements coverage · ③ Execution completeness · ④ Exit criteria

## Reports & Preview

| Command | Description |
|---------|-------------|
| `ftest report strategy` | Generate strategy HTML |
| `ftest report sprint` | Generate sprint test report |
| `ftest report closure [--summary "..."]` | Generate closure report |
| `ftest preview` | Serve reports locally (kills previous server) |
| `ftest preview --pdf <html>` | Export HTML report to PDF |
