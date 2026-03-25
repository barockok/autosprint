# Sprint Skill Design

**Date:** 2026-03-25
**Status:** Approved

## Overview

Sprint is a multi-agent feature development skill for Claude Code that dispatches 5 specialized agents (Dev, QA, UI, Security, TPM) in iterative rounds with consensus gating, real E2E testing, and documentation validation.

The skill auto-detects the project's tech stack and each agent adapts its tooling accordingly. It integrates with the existing superpowers workflow chain: `/brainstorm` → `/write-plan` → `/sprint` → `/simplify` → `/finish-branch`.

## Agent Roles

| Agent | Role | Worktree | Writes Code |
|-------|------|----------|-------------|
| Dev | Implements feature per spec, writes unit tests, fixes reviewer feedback | Own (isolated) | Yes |
| QA | Writes & runs real E2E tests — auto-selects tooling per tech stack | Own (isolated) | Yes (tests only) |
| UI | Structural validation (component tree, accessibility, design system) + interactive validation (browser automation of UX flows) | Reads Dev's worktree | No — produces findings |
| Security | OWASP Top 10, dependency audit, secrets scanning, auth/authz review | Reads Dev's worktree | No — produces findings |
| TPM | Validates README.md & docs ensure clone-run-replicate. Has override power on consensus gate. | Reads Dev's worktree | No — produces findings |

## Execution Model

All agents are dispatched via the **Agent tool** (subagents within a single orchestrating session). Dev and QA use `isolation: worktree` for write safety. UI, Security, and TPM read from Dev's worktree.

This approach was chosen over:
- **Agent Teams** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) — experimental, API may change
- **Manual tmux sessions** — cannot be orchestrated by a skill
- **Shared worktree for all** — QA needs write isolation for E2E tests

## Workflow

### Phase 1: Setup

1. Auto-detect tech stack (scan project files)
2. UI agent produces design spec / component structure upfront (before Dev starts)
3. Orchestrator creates task list from feature spec, splits into slices

### Phase 2: Iterative Rounds (per slice)

```
Round N:
├── Dev implements slice (worktree, unit tests, commits)
│
├── Parallel dispatch (all 4 at once):
│   ├── QA: writes & runs E2E tests (own worktree)
│   ├── UI: structural + interactive validation (reads Dev worktree)
│   ├── Security: OWASP audit, deps, secrets (reads Dev worktree)
│   └── TPM: validates README, run instructions (reads Dev worktree)
│
├── Consensus Gate:
│   ├── All 4 pass → merge QA tests into Dev branch → next slice
│   ├── Any fail → Dev gets findings → Round N+1
│   └── TPM override → stop early if remaining issues trivial
│
└── Safety net: max rounds (default 3, configurable)
```

### Phase 3: Completion

1. All slices done, all agents approved
2. QA's E2E tests merged into Dev branch
3. TPM does final README validation
4. Orchestrator presents summary to user

### Consensus Gate Rules

- Each agent votes: `PASS` or `FAIL(reasons)`
- All 4 PASS → slice approved
- Any FAIL → Dev receives consolidated findings, fixes, triggers re-review
- TPM can vote `OVERRIDE(reasons)` to force-pass trivial remaining issues
- Max rounds hit → TPM compiles remaining issues, presents to user for decision

## Tech Stack Auto-Detection

The orchestrator scans the project root:

| Detection | Stack | QA Tool | UI Validation | Security Focus |
|-----------|-------|---------|---------------|----------------|
| package.json + react/vue/svelte/angular | web-frontend | Playwright | Browser automation | XSS, CSP, CORS |
| package.json + express/fastify/hono/next | web-backend | Supertest/httpx | N/A (API only) | SQLi, auth, IDOR |
| Podfile or *.xcodeproj | ios | XCTest / Detox | Simulator interaction | Keychain, ATS, data leaks |
| build.gradle or AndroidManifest.xml | android | Maestro / Espresso | Emulator interaction | Intent injection, storage |
| pubspec.yaml (flutter) | mobile-cross-platform | Detox or Maestro | Simulator/emulator | Platform-specific |
| package.json + electron | desktop-electron | Playwright | Window automation | Node integration, IPC |
| Cargo.toml + tauri | desktop-tauri | Playwright | Window automation | IPC, command injection |
| Cargo.toml (no tauri) | cli-rust | Shell-based E2E | N/A | Input validation, path traversal |
| go.mod | cli-go | Shell-based E2E | N/A | Input validation, path traversal |
| pyproject.toml or setup.py | python | pytest + E2E | N/A if no UI | Dependency audit, injection |
| Multiple detected | multi-platform | Covers each | Covers each | Covers each |

## Robustness & State Management

### State Persistence

The skill creates `.sprint/` in the project root (added to `.gitignore`):

```
.sprint/
├── state.json              # Master state: phase, round, agent statuses
├── config.json             # Invocation config (max rounds, tech stack, slices)
├── watchdog.py             # Watchdog script (generated & executed)
├── rounds/
│   ├── round-1/
│   │   ├── dev-report.json
│   │   ├── qa-report.json
│   │   ├── ui-report.json
│   │   ├── security-report.json
│   │   └── tpm-report.json
│   └── round-N/...
└── logs/
    ├── agent-dev.log
    └── ...
```

### state.json Structure

```json
{
  "feature": "add user authentication",
  "techStack": ["web", "react", "node"],
  "currentSlice": 2,
  "totalSlices": 4,
  "currentRound": 1,
  "maxRounds": 3,
  "phase": "reviewing",
  "agents": {
    "dev":      { "status": "completed", "worktree": ".sprint/worktrees/dev", "lastActivity": "2026-03-25T10:30:00Z" },
    "qa":       { "status": "running",   "worktree": ".sprint/worktrees/qa",  "lastActivity": "2026-03-25T10:31:00Z" },
    "ui":       { "status": "running",   "lastActivity": "2026-03-25T10:31:05Z" },
    "security": { "status": "pending",   "lastActivity": null },
    "tpm":      { "status": "pending",   "lastActivity": null }
  },
  "consensus": {
    "round-1": { "qa": null, "ui": null, "security": null, "tpm": null }
  }
}
```

### Watchdog

`watchdog.py` runs as a background process and monitors:

- **Heartbeat**: each agent updates `lastActivity` every action. Watchdog checks every 30s.
- **Stall detection**: agent idle >3 minutes while `status: "running"` → flagged.
- **Timeout**: agent exceeds max time (default 10 min per agent per round) → `TIMEOUT` status.
- **Round completion**: all 4 reviewers have written reports → signals orchestrator.
- **Crash recovery**: `state.json` shows `phase: "reviewing"` but no agents running → signal to re-dispatch.

### Anti-Idle Guarantees

| Scenario | Detection | Response |
|----------|-----------|----------|
| Agent stalls | Watchdog: >3min idle | Orchestrator re-dispatches |
| Agent crashes | Status "running", no report | Orchestrator dispatches replacement |
| Agent times out | Watchdog writes TIMEOUT | Log, proceed with available reports, flag to user |
| All reviewers done | All reports written | Watchdog sets `phase: "consensus_ready"` |
| Session interrupted | state.json persists | Next session resumes from saved state |

## TPM Validation Levels

| Level | When | What TPM Does |
|-------|------|---------------|
| L1: Doc Review | Always | README structure, completeness, no broken references |
| L2: Dry Run | Always | Runs install, build, lint — verifies they succeed |
| L3: Full Run | If possible (no missing deps/creds) | Starts app, runs tests, hits endpoints |
| L4: Containerized | If Dockerfile/docker-compose exists | Builds and runs in Docker |

TPM auto-detects achievable level. Missing credentials → recommendation to improve docs, not a failure.

## Kanban Dashboard

Markdown tables displayed at: iteration start, subtask start, agent completion, consensus gate.

### Agent Status Table

| Agent | Pending | In Progress | Done | Verdict |
|-------|---------|-------------|------|---------|
| Dev | | | Implemented | committed |
| QA | | Running E2E | | |
| UI | | Validating | | |
| Security | Waiting | | | |
| TPM | Waiting | | | |

### Consensus Table

| Agent | Vote | Summary |
|-------|------|---------|
| QA | PASS | 8/8 E2E tests passing |
| UI | FAIL | Missing loading state on /callback route |
| Security | PASS | No issues found |
| TPM | PASS | L2 validated, docs updated |

### Overall Progress Table

| Slice | Status | Rounds | Agents | Notes |
|-------|--------|--------|--------|-------|
| 1. Auth | Done | 1/3 | 5/5 | First-pass clean |
| 2. OAuth | Round 2 | 2/3 | 4/5 | UI flagged missing state |
| 3. RBAC | Pending | — | — | |
| 4. Docs | Pending | — | — | |

All tables are GFM markdown — renders natively in Claude Code terminal, GitHub, and web.

`lib/state-manager.py` provides `render_kanban(state, fmt="markdown"|"json")`.

## Boris Workflow Integration

| Boris Tip | Sprint Feature |
|-----------|---------------|
| #1 Parallel Execution | QA, UI, Security, TPM run as parallel subagents |
| #2 Use Opus | Recommend Opus for Dev/QA, allow Haiku/Sonnet for reviewers |
| #3 Plan Mode | Sprint expects spec/plan as input — pairs with brainstorm → write-plan |
| #4 CLAUDE.md | TPM validates docs; orchestrator updates CLAUDE.md with learned patterns |
| #6 Subagents | Core architecture — fresh subagent per role |
| #7 Hooks | PostToolUse auto-formats Dev code; Stop hook for watchdog |
| #10 Challenge Claude | Security agent is adversarial; QA proves, never assumes |
| #14 Verification | Every agent has concrete verification — no claims without proof |
| #28 Worktree Isolation | Dev and QA get isolation: worktree |
| #29 /simplify | After all rounds, final simplification pass |
| #41 PostCompact | Re-inject agent context after compaction |

### Recommended Workflow Chain

```
/brainstorm → /write-plan → /sprint → /simplify → /finish-branch
```

## Distribution

### File Structure

```
sprint/
├── README.md                    # Install instructions, usage, examples
├── install.sh                   # curl-installable script
├── LICENSE
├── SKILL.md                     # Main skill (orchestrator logic)
├── agents/
│   ├── dev-agent.md
│   ├── qa-agent.md
│   ├── ui-agent.md
│   ├── security-agent.md
│   └── tpm-agent.md
├── lib/
│   ├── watchdog.py
│   ├── state-manager.py
│   └── tech-detect.py
├── templates/
│   ├── state.json
│   └── config.json
└── docs/
    └── architecture.md
```

### Install Methods

1. **curl one-liner**: `curl -fsSL https://raw.githubusercontent.com/<user>/sprint/main/install.sh | bash`
2. **git clone**: `git clone ... && bash install.sh`
3. **project-level**: `bash install.sh --project` (copies into `.claude/skills/sprint/`)
4. **Future marketplace**: plugin-compatible structure, no restructuring needed

### Invocation

```
/sprint add user authentication with OAuth2
/sprint --max-rounds 5 --skip-security add payment processing
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| max-rounds | 3 | Safety net for iterative rounds |
| skip-security | false | Skip security agent |
| skip-ui | false | Skip UI agent |
| skip-tpm | false | Skip TPM agent |
| stall-threshold | 180s | Watchdog stall detection |
| agent-timeout | 600s | Max time per agent per round |

## Decisions & Trade-offs

1. **Agent tool over Agent Teams** — stability over experimental features
2. **Hybrid worktree model** — Dev and QA isolated, reviewers read-only — balances isolation with simplicity
3. **Spec-driven over TDD** — clearer ownership: Dev owns unit tests, QA owns E2E
4. **Iterative rounds over Dev-first** — extreme confirmation requires multiple passes
5. **TPM validation levels** — pragmatic over idealistic: never fail because credentials missing
6. **Markdown kanban over ASCII** — universal rendering across terminal, web, GitHub
