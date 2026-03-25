#!/usr/bin/env bash
set -euo pipefail

# Sync version across all files that contain it.
# Source of truth: SKILL.md frontmatter `version: X.Y.Z`
#
# Files that must match:
#   - SKILL.md (frontmatter + "AutoSprint vX.Y.Z" print line)
#   - .claude-plugin/marketplace.json (top-level + plugin version)
#   - claude-plugin/.claude-plugin/plugin.json
#   - claude-plugin/skills/autosprint/SKILL.md (copy of SKILL.md)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Extract version from SKILL.md frontmatter
VERSION=$(grep -m1 '^version:' "$REPO_ROOT/SKILL.md" | sed 's/version: *//')

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not extract version from SKILL.md frontmatter"
    exit 1
fi

ERRORS=0

check_file() {
    local file="$1"
    local pattern="$2"
    local label="$3"

    if [[ ! -f "$file" ]]; then
        echo "MISSING: $file"
        ERRORS=$((ERRORS + 1))
        return
    fi

    if ! grep -q "$pattern" "$file"; then
        echo "MISMATCH: $label — expected version $VERSION in $file"
        ERRORS=$((ERRORS + 1))
    fi
}

# Check marketplace.json (has version twice: top-level and inside plugins array)
check_file "$REPO_ROOT/.claude-plugin/marketplace.json" "\"version\": \"$VERSION\"" "marketplace.json"

# Check plugin.json
check_file "$REPO_ROOT/claude-plugin/.claude-plugin/plugin.json" "\"version\": \"$VERSION\"" "plugin.json"

# Check SKILL.md print line
check_file "$REPO_ROOT/SKILL.md" "AutoSprint v$VERSION" "SKILL.md print line"

# Check plugin copy of SKILL.md is in sync
PLUGIN_SKILL="$REPO_ROOT/claude-plugin/skills/autosprint/SKILL.md"
if [[ -f "$PLUGIN_SKILL" ]]; then
    if ! diff -q "$REPO_ROOT/SKILL.md" "$PLUGIN_SKILL" > /dev/null 2>&1; then
        echo "MISMATCH: claude-plugin/skills/autosprint/SKILL.md is not in sync with SKILL.md"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "MISSING: $PLUGIN_SKILL"
    ERRORS=$((ERRORS + 1))
fi

# Check plugin copies of agent prompts
for agent in dev-agent qa-agent ui-agent security-agent tpm-agent; do
    SRC="$REPO_ROOT/agents/${agent}.md"
    DST="$REPO_ROOT/claude-plugin/skills/autosprint/agents/${agent}.md"
    if [[ -f "$SRC" ]] && [[ -f "$DST" ]]; then
        if ! diff -q "$SRC" "$DST" > /dev/null 2>&1; then
            echo "MISMATCH: claude-plugin/skills/autosprint/agents/${agent}.md not in sync"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

# Check plugin copies of lib files
for lib in __init__.py tech_detect.py state_manager.py watchdog.py agent_selector.py; do
    SRC="$REPO_ROOT/lib/${lib}"
    DST="$REPO_ROOT/claude-plugin/skills/autosprint/lib/${lib}"
    if [[ -f "$SRC" ]] && [[ -f "$DST" ]]; then
        if ! diff -q "$SRC" "$DST" > /dev/null 2>&1; then
            echo "MISMATCH: claude-plugin/skills/autosprint/lib/${lib} not in sync"
            ERRORS=$((ERRORS + 1))
        fi
    elif [[ -f "$SRC" ]] && [[ ! -f "$DST" ]]; then
        echo "MISSING: $DST (exists in lib/ but not in plugin)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check plugin copies of templates
for tmpl in state.json config.json; do
    SRC="$REPO_ROOT/templates/${tmpl}"
    DST="$REPO_ROOT/claude-plugin/skills/autosprint/templates/${tmpl}"
    if [[ -f "$SRC" ]] && [[ -f "$DST" ]]; then
        if ! diff -q "$SRC" "$DST" > /dev/null 2>&1; then
            echo "MISMATCH: claude-plugin/skills/autosprint/templates/${tmpl} not in sync"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

if [[ $ERRORS -gt 0 ]]; then
    echo ""
    echo "Found $ERRORS sync issue(s). Run 'bash scripts/sync-plugin.sh' to fix."
    exit 1
fi

echo "All files in sync at version $VERSION"
