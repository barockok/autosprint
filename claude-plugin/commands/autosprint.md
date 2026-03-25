---
allowed-tools: Agent, Bash, Read, Write, Edit, Glob, Grep, Skill
description: Launch multi-agent feature development with 5 agents (Dev, QA, UI, Security, TPM) in iterative consensus rounds
---

# /autosprint

You are launching AutoSprint — a multi-agent feature development workflow.

**REQUIRED:** Invoke the `autosprint` skill and follow it exactly.

## Arguments

The user's input after `/autosprint` is the feature description. Parse it for:
- **Feature description** — everything that isn't a flag
- **--max-rounds N** — max review iterations per slice (default: 3)
- **--skip-security** — skip the security agent
- **--skip-ui** — skip the UI agent
- **--skip-tpm** — skip the TPM agent

## Example

```
/autosprint add user authentication with OAuth2
/autosprint --max-rounds 5 add payment processing
/autosprint --skip-security add landing page
```

User input: $ARGUMENTS
