# Changelog

## [1.1.1] - 2026-03-25

### Fixed
- **Hard gate to prevent skill bypass** — Claude was skipping the workflow for "simple" tasks. Added `<HARD-GATE>` to SKILL.md and command file that explicitly forbids handling tasks directly when `/autosprint` is invoked.
- Removing features is now a valid use case in "When to Use" section.

## [1.1.0] - 2026-03-25

### Added
- **Intelligent agent selection** — auto-selects reviewers based on what files Dev changed. CSS-only change? Just UI agent. Auth code? Security agent. No more dispatching all 5 agents for every change.
- **Pair principle** — minimum Dev + 1 reviewer, always. No one works alone, but unnecessary agents stay home.
- **Token usage tracking** — records tokens per agent per round. Displays per-round breakdown, per-agent totals, and grand total at completion.
- **`--all-agents` flag** — force all 4 reviewers when you want comprehensive review.
- **`--agents` flag** — manually pick reviewers: `--agents qa,security`.
- **Scope constraints** — each reviewer only reads files Dev changed, not the entire codebase.
- **Model recommendations** — haiku for TPM, sonnet for UI/Security, opus for QA. ~60-70% cost reduction on review agents.
- **Kanban display at every trigger point** — explicit instructions ensure tables are always shown to the user.
- **README.md update ownership** — Dev agent now explicitly owns README updates. TPM validates them.
- **Native Claude Code plugin structure** — installable via `/plugins` marketplace.

### Fixed
- Kanban tables now actually display (concrete Python commands with "output to user" instructions)
- SKILL.md uses resolvable paths instead of `<skill-dir>` placeholders
- Fixed "AutoAutoSprint" double rename artifact
- Fixed status names (running/completed instead of in_progress/done)
- File locking with fcntl.flock for concurrent state writes
- Input validation for agent names, statuses, and votes
- Gitignore uses line-by-line matching instead of substring
- Watchdog handles naive timestamps and missing state files
- `.env.example` and `build.gradle.kts` now detected correctly

## [1.0.0] - 2026-03-25

### Added
- Initial release
- 5 specialized agents: Dev, QA, UI, Security, TPM
- Iterative consensus rounds with configurable max (default 3)
- Tech stack auto-detection (React, Vue, Angular, Express, iOS, Android, Flutter, Electron, Tauri, Rust, Go, Python)
- Real E2E testing (Playwright, Detox, Maestro — never mocks)
- Structural + interactive UI validation
- OWASP Top 10 security audit
- TPM validation levels L1-L4 (doc review, dry run, full run, containerized)
- State persistence in `.autosprint/` with crash recovery
- Watchdog monitoring (heartbeat, stall detection, timeout)
- GFM markdown kanban dashboards
- Install script with personal and project-level modes
- Optional integration with superpowers and frontend-design plugins
- Inspired by Karpathy's autoresearch and Udit Goenka's Claude skill
