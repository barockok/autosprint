# AutoSprint

Multi-agent feature development skill for Claude Code. Dispatches 5 specialized agents (Dev, QA, UI, Security, TPM) in iterative rounds with consensus gating.

## Install

### Prerequisites

1. [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and working
2. Python 3.8+ available on your PATH
3. Git installed (for worktree isolation)

### Step 1: Install required plugins

AutoSprint depends on two plugins from the official Claude Code marketplace. Open Claude Code and run:

```
/plugins
```

Then enable these plugins:
- **superpowers** (`superpowers@claude-plugins-official`) — provides `/brainstorm`, `/write-plan`, `/simplify`, `/finish-branch`
- **frontend-design** (`frontend-design@claude-plugins-official`) — used by UI agent for design spec generation

Or add them directly to your `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true,
    "frontend-design@claude-plugins-official": true
  }
}
```

> **Note:** If you don't have the `claude-plugins-official` marketplace, add it first via `/plugins` and follow the marketplace setup prompts.

### Step 2: Install AutoSprint

**Option A — Quick install (curl):**

```bash
curl -fsSL https://raw.githubusercontent.com/barockok/autosprint/main/install.sh | bash
```

This copies the skill to `~/.claude/skills/autosprint/` — available in all your projects.

**Option B — From source:**

```bash
git clone https://github.com/barockok/autosprint.git
cd autosprint && bash install.sh
```

**Option C — Project-level (for teams):**

```bash
# From within your project directory
git clone https://github.com/barockok/autosprint.git /tmp/autosprint
bash /tmp/autosprint/install.sh --project
git add .claude/skills/autosprint/
git commit -m "Add autosprint skill"
```

This installs to `.claude/skills/autosprint/` in your project — your team gets it via git.

### Step 3: Verify installation

Open Claude Code in any project and run:

```
/autosprint --help
```

Or simply start using it:

```
/autosprint add user authentication
```

### Recommended permissions

Add these to your project's `.claude/settings.json` to reduce permission prompts during sprint runs:

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 *)",
      "Bash(playwright *)",
      "Edit(.autosprint/**)"
    ]
  }
}
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
- `superpowers@claude-plugins-official` plugin (workflow chain: `/brainstorm`, `/write-plan`, `/simplify`, `/finish-branch`)
- `frontend-design@claude-plugins-official` plugin (UI agent design spec generation)

## Architecture

See [docs/architecture.md](docs/architecture.md) for technical details.

## Inspiration & Credits

AutoSprint builds on the **autonomous iteration** concept pioneered by [Andrej Karpathy's autoresearch](https://github.com/karpathy/autoresearch) -- the idea that an agent can autonomously modify, verify, keep or discard, and repeat until a goal is met.

[Udit Goenka's autoresearch Claude skill](https://github.com/uditgoenka/autoresearch) brought that concept into Claude Code as a reusable skill, proving the loop works for any task with a measurable metric.

AutoSprint extends this foundation with **multi-agent personas for feature development**:

- Instead of one agent iterating alone, **5 specialized agents** (Dev, QA, UI, Security, TPM) work in parallel -- each with a different concern and verification method.
- Instead of a single metric, a **consensus gate** requires independent approval from all reviewers before proceeding.
- Instead of generic verification, agents perform **real E2E testing**, **structural UI validation**, **OWASP security audits**, and **documentation verification** against the actual running application.
- A **robustness layer** (state persistence, watchdog, crash recovery) keeps the autonomous loop running reliably across long sessions.

The core insight from autoresearch -- autonomous goal-directed iteration with verification -- remains the beating heart. AutoSprint puts it on steroids with specialized agents who each bring a different lens to the same work.

## License

MIT
