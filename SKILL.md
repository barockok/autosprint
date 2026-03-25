---
name: autosprint
description: Use when developing features that need multi-agent validation with parallel review — dispatches Dev, QA, UI, Security, and TPM agents in iterative consensus rounds with real E2E testing, structural UI validation, security audit, and documentation verification
---

# AutoSprint — Multi-Agent Feature Development

## Overview

AutoSprint dispatches 5 specialized agents in iterative rounds to build, test, validate, and document features with extreme confirmation. Each round follows the cycle: Dev implements, then QA + UI + Security + TPM review in parallel, then a consensus gate decides whether to fix or proceed.

Core principle: No feature ships until Dev, QA, UI, Security, and TPM all approve through independent verification.

## When to Use / When Not to Use

**Use AutoSprint when:**
- Building a new feature that needs comprehensive validation
- The change touches UI components, security-sensitive code, or public documentation
- You need parallel review from multiple disciplines before merging

**Do NOT use AutoSprint when:**
- Fixing a quick, isolated bug
- Pure refactoring with no behavioral change
- Exploratory prototyping or spike work

## Agents

| Agent    | Job                                           | Isolation          | Writes Code |
|----------|-----------------------------------------------|--------------------|-------------|
| Dev      | Implements feature slices, updates README.md  | Own worktree       | Yes         |
| QA       | Writes and runs real E2E tests                | Own worktree       | Yes (tests) |
| UI       | Validates structure, accessibility, responsive| Reads Dev worktree | No          |
| Security | Audits for vulnerabilities and secret leaks   | Reads Dev worktree | No          |
| TPM      | Verifies README.md enables clone-run-replicate| Reads Dev worktree | No          |

## Invocation

```
/autosprint add user authentication with OAuth2
/autosprint --max-rounds 5 --skip-security add payment processing
```

| Parameter         | Default | Description                                |
|-------------------|---------|--------------------------------------------|
| `--max-rounds`    | 3       | Maximum review rounds per slice            |
| `--skip-security` | false   | Skip the Security agent                    |
| `--skip-ui`       | false   | Skip the UI agent                          |
| `--skip-tpm`      | false   | Skip the TPM agent                         |

## Orchestrator Instructions

**IMPORTANT:** You are the orchestrator. Follow these steps exactly. When the instructions say "display kanban", you MUST run the Python command and output the resulting markdown table to the user. Do not skip kanban displays.

### Resolving Paths

Before starting, determine these paths:
- **SKILL_DIR**: The directory where this SKILL.md lives (contains `agents/`, `lib/`, `templates/`)
- **PROJECT_DIR**: The user's current working directory (where the feature is being built)

All Python commands below use these paths. For example:
```bash
python3 SKILL_DIR/lib/tech_detect.py PROJECT_DIR
```

### Step 1: Initialize

1. **Parse** the user's input. Extract flags (`--max-rounds N`, `--skip-security`, `--skip-ui`, `--skip-tpm`). Everything else is the **feature description**.

2. **Detect tech stack:**
   ```bash
   python3 SKILL_DIR/lib/tech_detect.py PROJECT_DIR
   ```
   This outputs JSON with `stacks`, `qa_tool`, `ui_validation`, `security_focus`.

3. **Initialize state:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import init_sprint
   init_sprint('PROJECT_DIR', 'FEATURE_DESCRIPTION', TECH_STACKS, max_rounds=MAX_ROUNDS, slices=SLICE_LIST)
   "
   ```

4. **Start watchdog** in background:
   ```bash
   python3 SKILL_DIR/lib/watchdog.py PROJECT_DIR --loop &
   ```

5. **Display kanban — run this and output the result:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import render_overview
   print(render_overview('PROJECT_DIR'))
   "
   ```
   **Copy the markdown table output and display it to the user.**

### Step 2: UI Design Spec (Phase 1)

1. **Dispatch UI agent** using the Agent tool:
   - Load the prompt from `SKILL_DIR/agents/ui-agent.md`
   - Fill in template variables: `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{uiValidation}}`, `{{currentRound}}`, `{{maxRounds}}`
   - Tell the UI agent to run **Phase 1 only** (design spec, no validation yet)
   - If the `frontend-design` skill is available, tell the UI agent to invoke it

2. **Store the design spec** — save the UI agent's output for use in Step 3.

3. **Display kanban:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, render_kanban
   update_agent_status('PROJECT_DIR', 'ui', 'completed')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

### Step 3: Dev Implementation (per slice)

For each slice:

1. **Display overview kanban:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import render_overview
   print(render_overview('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

2. **Dispatch Dev agent** using the Agent tool with `isolation: worktree`:
   - Load the prompt from `SKILL_DIR/agents/dev-agent.md`
   - Fill in template variables: `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{uiDesignSpec}}`, `{{currentRound}}`, `{{maxRounds}}`
   - If this is round > 1, include `{{reviewerFindings}}` with consolidated findings from prior round
   - **IMPORTANT:** Tell Dev to update README.md with:
     - Project description
     - Install/setup instructions
     - How to run the app
     - How to run tests
     - Any new environment variables or configuration

3. **Update status and display kanban:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, render_kanban
   update_agent_status('PROJECT_DIR', 'dev', 'running', phase='implementing')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

4. **Wait for Dev to complete**, then update status:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, render_kanban
   update_agent_status('PROJECT_DIR', 'dev', 'completed', phase='reviewing')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

### Step 4: Parallel Review

1. **Display kanban showing reviewers starting:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, render_kanban
   update_agent_status('PROJECT_DIR', 'qa', 'running')
   update_agent_status('PROJECT_DIR', 'ui', 'running')
   update_agent_status('PROJECT_DIR', 'security', 'running')
   update_agent_status('PROJECT_DIR', 'tpm', 'running')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

2. **Dispatch ALL active reviewers IN PARALLEL** using multiple Agent tool calls in one message (respect `--skip-*` flags):

   **CRITICAL — Token Optimization:** To keep review agents fast and cheap, you MUST:
   - Pass only the **list of files changed by Dev** (from Dev's report), not the entire codebase
   - Tell each reviewer to **ONLY read the files Dev changed** — do not explore the rest of the project
   - Use `model: haiku` for TPM agent (lightweight doc validation)
   - Use `model: sonnet` for Security and UI agents (medium complexity)
   - Use `model: opus` for QA agent only (needs to write and run tests)

   - **QA Agent** — `isolation: worktree`, `model: opus`
     - Load prompt from `SKILL_DIR/agents/qa-agent.md`
     - Fill in `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{qaTool}}`, `{{currentRound}}`, `{{maxRounds}}`
     - Include `{{filesChanged}}` — the list of files Dev changed

   - **UI Agent (Phase 2)** — reads Dev worktree, `model: sonnet`
     - Load prompt from `SKILL_DIR/agents/ui-agent.md`
     - Fill in template variables, tell it to run **Phase 2 only** (validation)
     - Include `{{filesChanged}}` — only validate these files, not the entire project

   - **Security Agent** — reads Dev worktree, `model: sonnet`
     - Load prompt from `SKILL_DIR/agents/security-agent.md`
     - Fill in `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{securityFocus}}`, `{{currentRound}}`, `{{maxRounds}}`
     - Include `{{filesChanged}}` — only audit these files, not the entire codebase

   - **TPM Agent** — reads Dev worktree, `model: haiku`
     - Load prompt from `SKILL_DIR/agents/tpm-agent.md`
     - Fill in `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{currentRound}}`, `{{maxRounds}}`
     - TPM only needs to read README.md and run the commands in it

3. **As each agent completes**, record their vote and update kanban:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, record_vote, render_kanban
   update_agent_status('PROJECT_DIR', 'AGENT_NAME', 'completed')
   record_vote('PROJECT_DIR', ROUND_NUM, 'AGENT_NAME', 'VOTE', 'SUMMARY')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user after EACH agent completes.**

### Step 5: Consensus Gate

1. **Run watchdog check:**
   ```bash
   python3 SKILL_DIR/lib/watchdog.py PROJECT_DIR --once
   ```

2. **Display consensus table:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import render_consensus, check_consensus
   print(render_consensus('PROJECT_DIR', ROUND_NUM))
   result = check_consensus('PROJECT_DIR', ROUND_NUM)
   print(f'\n**Decision: {result}**')
   "
   ```
   **Output the consensus table AND decision to the user.**

3. **Act on the decision:**

   - **APPROVED** — Merge QA tests into the Dev branch. Advance to next slice (back to Step 3) or completion (Step 6).

   - **REJECTED** — Consolidate all FAIL findings into a single brief. Go back to Step 3 with the consolidated findings as `{{reviewerFindings}}`. Increment the round counter.

   - **PENDING** — Wait and re-check. Run watchdog to detect stalls.

4. **Max rounds reached** — If `currentRound >= maxRounds` and still REJECTED, dispatch TPM to compile a final status report. Present the report to the user and ask: "Force-proceed or abort?"

### Step 6: Completion

1. Merge any remaining QA E2E tests into the Dev branch.
2. Run a **final TPM validation** — dispatch TPM agent one last time to verify README.md and docs are complete.
3. **Display final overview kanban:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import render_overview
   print(render_overview('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**
4. **Present summary** to the user:
   - Slices completed
   - Total rounds used per slice
   - Consensus votes per agent
   - Any outstanding warnings
5. Clean up: kill the watchdog background process.

## Kanban Display Rules

**You MUST display kanban tables at these trigger points — never skip them:**

| Trigger | What to display |
|---------|----------------|
| After initialization | `render_overview` |
| Before Dev starts a slice | `render_overview` |
| When Dev starts working | `render_kanban` |
| When Dev completes | `render_kanban` |
| When reviewers start | `render_kanban` |
| When each reviewer completes | `render_kanban` |
| At consensus gate | `render_consensus` |
| After all slices done | `render_overview` |

To display a kanban, run the Python command and **copy the markdown output into your response**. The user must see the table.

## README.md Update Rules

**Dev agent MUST update README.md as part of every feature implementation.** The README must include:
- Project description
- Prerequisites and dependencies
- Installation / setup instructions
- How to run the application
- How to run tests
- Environment variables and configuration
- Any new API endpoints, CLI commands, or user-facing changes from this feature

**TPM agent validates the README** — if it's missing, incomplete, or commands don't work, TPM votes FAIL.

## State Management

All state persists in `.autosprint/` directory (auto-added to `.gitignore`):
- `.autosprint/state.json` — phase, round, agent statuses, consensus votes
- `.autosprint/config.json` — feature, tech stack, max rounds, flags
- `.autosprint/rounds/round-N/` — agent reports per round

If a session is interrupted, read `.autosprint/state.json` on next invocation and resume from the current phase.

## Integration

**Recommended chain (requires superpowers plugin):**
```
/brainstorm → /write-plan → /autosprint → /simplify → /finish-branch
```

**Standalone usage (no plugins needed):**
```
/autosprint add user authentication with OAuth2
```

AutoSprint works without any plugin dependencies. Optional plugins enhance the experience:

**Optional plugin dependencies:**
- `superpowers@claude-plugins-official` — Enables `/brainstorm`, `/write-plan`, `/simplify`, `/finish-branch`.
- `frontend-design@claude-plugins-official` — Enhances UI agent design specs.

**Agent prompt files:**
- `agents/dev-agent.md`
- `agents/qa-agent.md`
- `agents/ui-agent.md`
- `agents/security-agent.md`
- `agents/tpm-agent.md`

**Python library files:**
- `lib/tech_detect.py` — auto-detects project tech stack
- `lib/state_manager.py` — state, kanban rendering, consensus checking
- `lib/watchdog.py` — heartbeat monitoring, stall/timeout detection

## Red Flags — Never Do These

1. **Never skip the consensus gate.** Every round must pass through the gate.
2. **Never let Dev self-approve.** Dev does not vote. Only QA, UI, Security, and TPM vote.
3. **Never mock E2E tests.** QA must run real tests against the actual running application.
4. **Never ignore a TPM FAIL.** If README is broken or incomplete, it must be fixed.
5. **Never exceed max rounds silently.** Always surface to the user with a TPM report.
6. **Never skip kanban display.** Every trigger point in the table above MUST produce a visible kanban table in the output.
