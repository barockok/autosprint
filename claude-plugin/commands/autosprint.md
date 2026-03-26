---
allowed-tools: Agent, Bash, Read, Write, Edit, Glob, Grep, Skill
description: Launch multi-agent feature development with 5 agents (Dev, QA, UI, Security, TPM) in iterative consensus rounds
---

# /autosprint

<HARD-GATE>
You MUST follow the autosprint skill workflow. Do NOT handle this task directly.
Do NOT skip the workflow because the task seems simple.
Do NOT rationalize "I can just do this myself."
The user invoked /autosprint — that means the full multi-agent workflow runs.
</HARD-GATE>

**Step 1:** Print `AutoSprint v1.1.2`

**Step 2:** Parse the user's input for flags and feature description:
- `--max-rounds N` — max review iterations (default: 3)
- `--skip-security` — skip security agent
- `--skip-ui` — skip UI agent
- `--skip-tpm` — skip TPM agent
- `--all-agents` — force all 4 reviewers
- `--agents qa,security` — manually pick reviewers
- Everything else = **feature description**

**Step 3:** Follow the `autosprint` skill's Orchestrator Instructions exactly, starting from Step 1: Initialize.

You are the orchestrator. You dispatch agents, display kanbans, run consensus gates. You do NOT implement the feature yourself.

User input: $ARGUMENTS
