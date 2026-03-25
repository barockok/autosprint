# AutoSprint Architecture

## Execution Model

Orchestrator (main Claude Code session) dispatches agents via Agent tool.

- **Dev, QA**: `isolation: worktree` — write to own git worktrees
- **UI, Security, TPM**: read Dev's worktree, produce findings only

## State Management

`.autosprint/` directory persists all workflow state:

- `state.json` — master state (phase, round, agent statuses, consensus)
- `config.json` — invocation config
- `rounds/round-N/` — agent reports per round
- `logs/` — agent activity logs

All writes to `state.json` use `fcntl.flock` exclusive file locking to prevent concurrent write corruption.

## Watchdog

`lib/watchdog.py` monitors agent health:

- Heartbeat check every 30s
- Stall detection at 3min idle
- Timeout at 10min per agent per round
- Round completion detection (all reviewer reports present)
- Defensive timestamp parsing (handles naive and aware datetimes)

## Consensus Gate

4 reviewers vote: PASS, FAIL, or OVERRIDE (TPM only).

- All PASS → approved
- Any FAIL (no OVERRIDE) → rejected, Dev fixes
- TPM OVERRIDE → force-approve trivial issues
- Max rounds → escalate to user

## Tech Detection

`lib/tech_detect.py` scans project root for config files and maps to:

- QA testing tool (Playwright, Supertest, XCTest, Maestro, pytest, shell-e2e)
- UI validation approach (browser-automation, simulator, emulator, window-automation, none)
- Security focus areas (XSS, SQLi, keychain, intent-injection, etc.)

Supports multi-stack detection with merged security concerns.

## Kanban

`lib/state_manager.py` renders GFM markdown tables at trigger points:

- Agent status table (per round)
- Consensus table (after voting)
- Overview table (all slices)

All output is standard GitHub-Flavored Markdown — renders natively in Claude Code terminal, GitHub, and web.

## TPM Validation Levels

| Level | When | What |
|-------|------|------|
| L1: Doc Review | Always | README structure, completeness |
| L2: Dry Run | Always | install, build, lint succeed |
| L3: Full Run | If deps/creds available | App starts, tests pass |
| L4: Containerized | If Docker config exists | Build and run in container |

TPM never fails because it can't reach a higher level — reports as recommendation.

## Skill Dependencies

- **`superpowers` plugin** — Provides the workflow chain skills: `/brainstorm`, `/write-plan`, `/simplify`, `/finish-branch`. AutoSprint slots into this chain as the execution step.
- **`frontend-design`** — UI agent invokes this skill during Phase 1 to produce distinctive, production-grade design specs. Avoids generic AI aesthetics.

## Key Decisions

1. **Agent tool over Agent Teams** — stability over experimental features
2. **Hybrid worktree**: Dev + QA isolated, reviewers read-only
3. **Spec-driven**: Dev owns unit tests, QA owns E2E
4. **File locking**: fcntl.flock for concurrent state safety
5. **Markdown kanban**: universal rendering across all environments
6. **Pragmatic TPM**: validation levels adapt to what's possible
