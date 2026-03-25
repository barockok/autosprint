# AutoSprint

Multi-agent feature development skill for Claude Code. Dispatches 5 specialized agents (Dev, QA, UI, Security, TPM) in iterative rounds with consensus gating.

## Install

**Quick install:**

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/autosprint/main/install.sh | bash
```

**From source:**

```bash
git clone https://github.com/<user>/autosprint.git
cd autosprint && bash install.sh
```

**For your team (project-level):**

```bash
bash install.sh --project
git add .claude/skills/autosprint/
git commit -m "Add autosprint skill"
```

## Usage

```
/autosprint add user authentication with OAuth2
/autosprint --max-rounds 5 add payment processing
/autosprint --skip-security add landing page
```

## What It Does

1. **Detects your tech stack** -- scans project files, adapts agent tooling
2. **UI agent produces design spec** -- component tree, accessibility, interactions
3. **Dev implements per slice** -- in isolated worktree, with unit tests
4. **4 agents review in parallel:**
   - **QA** -- real E2E tests (Playwright, Detox, Maestro -- never mocks)
   - **UI** -- structural + interactive validation via browser automation
   - **Security** -- OWASP Top 10, CVE audit, secrets scan
   - **TPM** -- validates README enables clone-run-replicate
5. **Consensus gate** -- all must approve, or Dev fixes and re-submits
6. **Repeat** -- until approved or max rounds (default 3)

## Options

| Flag | Default | Description |
|------|---------|-------------|
| --max-rounds | 3 | Max review iterations per slice |
| --skip-security | false | Skip security agent |
| --skip-ui | false | Skip UI agent |
| --skip-tpm | false | Skip TPM agent |

## Workflow Integration

AutoSprint fits into the superpowers workflow chain:

```
/brainstorm -> /write-plan -> /autosprint -> /simplify -> /finish-branch
```

## Tech Stack Support

Auto-detects and adapts to:

| Stack | QA Tool | UI Validation |
|-------|---------|---------------|
| React, Vue, Svelte, Angular | Playwright | Browser automation |
| Express, Fastify, Next.js | Supertest | N/A (API only) |
| iOS (Podfile, xcodeproj) | XCTest / Detox | Simulator |
| Android (Gradle, Manifest) | Maestro / Espresso | Emulator |
| Flutter | Maestro | Simulator/emulator |
| Electron, Tauri | Playwright | Window automation |
| Rust CLI, Go CLI | Shell-based E2E | N/A |
| Python | pytest | N/A |

## How It Works

### State Management

AutoSprint creates a `.autosprint/` directory (auto-added to .gitignore) that tracks:
- Current phase, slice, and round
- Agent statuses with heartbeat timestamps
- Consensus votes per round
- Agent reports

### Watchdog

A background watchdog monitors agent health:
- Detects stalled agents (>3min idle)
- Enforces timeouts (>10min)
- Detects round completion

### Kanban Dashboard

Markdown tables displayed at key moments showing agent status, consensus votes, and overall progress. Renders natively in Claude Code terminal and GitHub.

## Requirements

- Claude Code with Agent tool support
- Python 3.8+ (for state management and watchdog)
- Git (for worktree isolation)
- `frontend-design` skill (used by UI agent for design spec generation -- install via `/plugin`)

## Architecture

See [docs/architecture.md](docs/architecture.md) for technical details.

## License

MIT
