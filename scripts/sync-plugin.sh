#!/usr/bin/env bash
set -euo pipefail

# Sync all plugin files from source of truth.
# Run this before committing to ensure plugin directory matches.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/claude-plugin/skills/autosprint"

# Extract version from SKILL.md
VERSION=$(grep -m1 '^version:' "$REPO_ROOT/SKILL.md" | sed 's/version: *//')

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not extract version from SKILL.md frontmatter"
    exit 1
fi

echo "Syncing to version $VERSION..."

# Update version in marketplace.json
sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/g" "$REPO_ROOT/.claude-plugin/marketplace.json"

# Update version in plugin.json
sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/g" "$REPO_ROOT/claude-plugin/.claude-plugin/plugin.json"

# Sync SKILL.md
cp "$REPO_ROOT/SKILL.md" "$PLUGIN_DIR/SKILL.md"

# Sync agents
for agent in dev-agent qa-agent ui-agent security-agent tpm-agent; do
    cp "$REPO_ROOT/agents/${agent}.md" "$PLUGIN_DIR/agents/${agent}.md"
done

# Sync lib
for lib in __init__.py tech_detect.py state_manager.py watchdog.py agent_selector.py; do
    if [[ -f "$REPO_ROOT/lib/${lib}" ]]; then
        cp "$REPO_ROOT/lib/${lib}" "$PLUGIN_DIR/lib/${lib}"
    fi
done

# Sync templates
for tmpl in state.json config.json; do
    cp "$REPO_ROOT/templates/${tmpl}" "$PLUGIN_DIR/templates/${tmpl}"
done

echo "Synced all files to version $VERSION"
