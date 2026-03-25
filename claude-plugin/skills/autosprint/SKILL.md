---
name: autosprint
version: 1.1.1
description: Use when developing features that need multi-agent validation with parallel review — dispatches Dev, QA, UI, Security, and TPM agents in iterative consensus rounds with real E2E testing, structural UI validation, security audit, and documentation verification
---

# AutoSprint — Multi-Agent Feature Development

<HARD-GATE>
You MUST follow this skill's workflow for EVERY task invoked through /autosprint. No exceptions.

Do NOT:
- Handle the task directly without dispatching agents
- Skip the workflow because the task "seems simple"
- Rationalize that "this doesn't need multi-agent review"

If /autosprint was invoked, the full workflow runs. Period. The user chose this skill deliberately.

If the task is genuinely wrong for AutoSprint (e.g., "what time is it?"), tell the user and suggest they run the task without /autosprint instead.
</HARD-GATE>

## Overview

AutoSprint dispatches 5 specialized agents in iterative rounds to build, test, validate, and document features with extreme confirmation. Each round: Dev implements → reviewers validate in parallel → consensus gate → fix or proceed.

## When to Use / When Not to Use

**Use AutoSprint when:**
- Building a new feature, modifying existing features, or removing features
- The change touches UI, security-sensitive code, or documentation
- You want multi-agent review before merging

**Do NOT use AutoSprint when:**
- Non-code tasks (questions, explanations, config lookups)
- Tell the user: "This task doesn't need AutoSprint. Run it directly without /autosprint."

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
| `--all-agents`    | false   | Force all 4 reviewers regardless of auto-selection |
| `--agents`        | auto    | Manually pick reviewers: `--agents qa,security` |

**Default behavior:** Reviewers are auto-selected based on what files Dev changes (see Step 3.5). Use `--all-agents` to force all 4, or `--agents qa,ui` to pick manually.

## Orchestrator Instructions

**IMPORTANT:** You are the orchestrator. Follow these steps exactly. When the instructions say "display kanban", you MUST run the Python command and output the resulting markdown table to the user. Do not skip kanban displays.

### Before Anything Else

**Print the skill version to the user:**

```
AutoSprint v1.1.1
```

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

### Step 3.5: Agent Selection

After Dev completes, **automatically select which reviewers are needed** based on what files changed. Do NOT always dispatch all 4 reviewers.

1. **Run agent selection:**
   ```bash
   python3 -c "
   import sys, json; sys.path.insert(0, 'SKILL_DIR')
   from lib.agent_selector import select_agents, render_selection
   files = FILES_CHANGED_JSON_ARRAY
   result = select_agents(files, 'FEATURE_DESCRIPTION')
   print(render_selection(result))
   print()
   print('JSON:', json.dumps(result))
   "
   ```
   Replace `FILES_CHANGED_JSON_ARRAY` with the list from Dev's report (e.g., `["src/App.tsx", "src/styles.css"]`).

   **Output the agent selection table to the user.**

2. **The pair principle:** Dev + at least 1 reviewer. Always. The selector enforces this — if no reviewer matches, QA is the default.

3. **User can override:** If the user explicitly asked for `--skip-*` flags or `--all-agents`, respect that over the auto-selection.

4. **Selection logic:**

   | Changed Files | Reviewers Selected |
   |---|---|
   | CSS/styles/components only | UI (+ QA if code logic changed) |
   | Backend/API/logic only | QA |
   | Auth/payment/secrets/.env | QA + Security |
   | UI + auth files | QA + UI + Security |
   | README/docs/config changed | TPM |
   | 10+ files changed | TPM (large change, docs likely need update) |
   | New project / first feature | All 4 |

### Step 4: Parallel Review

1. **Display kanban showing selected reviewers starting** (only set status for selected agents):
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, render_kanban
   # Only update status for SELECTED reviewers:
   for agent in SELECTED_REVIEWERS:
       update_agent_status('PROJECT_DIR', agent, 'running')
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **Output the markdown table to the user.**

2. **Dispatch ONLY the selected reviewers IN PARALLEL** using multiple Agent tool calls in one message:

   **Token optimization rules:**
   - Pass only `{{filesChanged}}` from Dev's report — reviewers ONLY read those files
   - Use `model: haiku` for TPM (lightweight doc validation)
   - Use `model: sonnet` for Security and UI (medium complexity)
   - Use `model: opus` for QA only (needs to write and run tests)

   **If QA was selected** — `isolation: worktree`, `model: opus`
   - Load prompt from `SKILL_DIR/agents/qa-agent.md`
   - Fill in `{{feature}}`, `{{techStack}}`, `{{sliceDescription}}`, `{{qaTool}}`, `{{currentRound}}`, `{{maxRounds}}`, `{{filesChanged}}`

   **If UI was selected** — reads Dev worktree, `model: sonnet`
   - Load prompt from `SKILL_DIR/agents/ui-agent.md`
   - Phase 2 only (validation). Include `{{filesChanged}}`

   **If Security was selected** — reads Dev worktree, `model: sonnet`
   - Load prompt from `SKILL_DIR/agents/security-agent.md`
   - Fill in all template vars. Include `{{filesChanged}}`

   **If TPM was selected** — reads Dev worktree, `model: haiku`
   - Load prompt from `SKILL_DIR/agents/tpm-agent.md`
   - Only reads README.md and runs commands in it

3. **As each agent completes**, record their vote, token usage, and update kanban:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import update_agent_status, record_vote, record_tokens, render_kanban
   update_agent_status('PROJECT_DIR', 'AGENT_NAME', 'completed')
   record_vote('PROJECT_DIR', ROUND_NUM, 'AGENT_NAME', 'VOTE', 'SUMMARY')
   record_tokens('PROJECT_DIR', ROUND_NUM, 'AGENT_NAME', TOKEN_COUNT)
   print(render_kanban('PROJECT_DIR'))
   "
   ```
   **TOKEN_COUNT** = the `total_tokens` value from the Agent tool result (visible in the agent's response metadata). Record it for every agent including Dev.
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
4. **Display token usage summary:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, 'SKILL_DIR')
   from lib.state_manager import render_token_summary
   print(render_token_summary('PROJECT_DIR'))
   "
   ```
   **Output the token summary table to the user.** This shows per-round breakdown, per-agent totals, and grand total.
5. **Present summary** to the user:
   - Slices completed
   - Total rounds used per slice
   - Consensus votes per agent
   - Token usage (from step 4)
   - Any outstanding warnings
6. Clean up: kill the watchdog background process.

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
