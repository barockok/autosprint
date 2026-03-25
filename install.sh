#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="autosprint"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine install target
if [[ "${1:-}" == "--project" ]]; then
    TARGET_DIR="$(pwd)/.claude/skills/${SKILL_NAME}"
    echo "Installing ${SKILL_NAME} skill to project: ${TARGET_DIR}"
else
    TARGET_DIR="${HOME}/.claude/skills/${SKILL_NAME}"
    echo "Installing ${SKILL_NAME} skill to: ${TARGET_DIR}"
fi

# Create target directory structure
mkdir -p "${TARGET_DIR}/agents"
mkdir -p "${TARGET_DIR}/lib"
mkdir -p "${TARGET_DIR}/templates"

# Copy skill file
cp "${REPO_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"

# Copy agent prompts
for agent in dev-agent qa-agent ui-agent security-agent tpm-agent; do
    cp "${REPO_DIR}/agents/${agent}.md" "${TARGET_DIR}/agents/${agent}.md"
done

# Copy lib files
for lib in __init__.py tech_detect.py state_manager.py watchdog.py; do
    if [[ -f "${REPO_DIR}/lib/${lib}" ]]; then
        cp "${REPO_DIR}/lib/${lib}" "${TARGET_DIR}/lib/${lib}"
    fi
done

# Copy templates
for tmpl in state.json config.json; do
    cp "${REPO_DIR}/templates/${tmpl}" "${TARGET_DIR}/templates/${tmpl}"
done

echo ""
echo "AutoSprint skill installed successfully!"
echo ""
echo "Usage:"
echo "  /autosprint <feature description>"
echo "  /autosprint --max-rounds 5 add user authentication"
echo ""
echo "Options:"
echo "  --max-rounds N    Max review iterations per slice (default: 3)"
echo "  --skip-security   Skip security agent"
echo "  --skip-ui         Skip UI agent"
echo "  --skip-tpm        Skip TPM agent"
echo ""
if [[ "${1:-}" == "--project" ]]; then
    echo "Tip: Commit .claude/skills/${SKILL_NAME}/ to share with your team."
fi
