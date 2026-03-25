"""Agent selection logic for autosprint.

Analyzes Dev's changed files to determine which review agents are needed.
The pair principle: minimum 2 agents always (Dev + at least 1 reviewer).

Usage:
    from lib.agent_selector import select_agents
    result = select_agents(files_changed, feature_description)

    # Or as CLI:
    python3 lib/agent_selector.py '["src/App.tsx","src/styles.css"]' 'add dark mode toggle'
"""
import json
import os
import sys

# File extension categories
UI_EXTENSIONS = {
    ".css", ".scss", ".sass", ".less", ".styl",
    ".tsx", ".jsx", ".vue", ".svelte",
    ".html", ".htm", ".ejs", ".hbs", ".pug",
}

UI_PATTERNS = {
    "component", "page", "layout", "view", "screen",
    "style", "theme", "css", "ui", "modal", "dialog",
    "button", "form", "nav", "header", "footer", "sidebar",
}

SECURITY_EXTENSIONS = {
    ".env", ".env.example", ".env.local",
    ".pem", ".key", ".crt", ".cert",
}

SECURITY_PATTERNS = {
    "auth", "login", "signup", "register", "password", "token",
    "jwt", "oauth", "session", "cookie", "credential",
    "encrypt", "decrypt", "hash", "salt", "secret",
    "api_key", "apikey", "access_key",
    "payment", "stripe", "billing", "checkout",
    "admin", "permission", "role", "rbac", "acl",
    "middleware", "guard", "policy",
    "sql", "query", "database", "migration",
    "upload", "download", "file",
    "cors", "csp", "helmet",
}

DOCS_PATTERNS = {
    "readme", "changelog", "contributing", "license",
    "docs/", "doc/", "documentation",
    ".md",
}

TEST_EXTENSIONS = {
    ".test.ts", ".test.tsx", ".test.js", ".test.jsx",
    ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx",
    "_test.go", "_test.py", ".test.py",
}

CONFIG_PATTERNS = {
    "package.json", "tsconfig", "webpack", "vite.config",
    "next.config", "tailwind.config", "postcss.config",
    "docker", "dockerfile", "docker-compose",
    "nginx", ".env", "config",
    "cargo.toml", "go.mod", "pyproject.toml",
    "ci", "cd", "github/workflows", "gitlab-ci",
}

# Feature description keywords that suggest specific agents
SECURITY_KEYWORDS = {
    "auth", "login", "signup", "password", "token", "jwt", "oauth",
    "payment", "stripe", "billing", "checkout", "encrypt", "secret",
    "admin", "permission", "role", "api key", "credential",
    "upload", "download", "file upload", "cors", "csrf",
    "sql", "injection", "xss", "sanitize", "validate",
}

UI_KEYWORDS = {
    "ui", "ux", "design", "layout", "responsive", "mobile",
    "component", "page", "screen", "dashboard", "form",
    "modal", "dialog", "button", "navigation", "menu",
    "theme", "dark mode", "light mode", "style", "css",
    "animation", "transition", "accessibility", "a11y",
}

DOCS_KEYWORDS = {
    "readme", "documentation", "docs", "guide", "tutorial",
    "api docs", "changelog", "setup", "install",
    "architecture", "diagram", "onboarding",
}


def _categorize_file(filepath):
    """Categorize a single file path into change types."""
    categories = set()
    lower = filepath.lower()
    base = os.path.basename(lower)
    ext = os.path.splitext(lower)[1]

    # Check UI
    if ext in UI_EXTENSIONS:
        categories.add("ui")
    for pattern in UI_PATTERNS:
        if pattern in lower:
            categories.add("ui")
            break

    # Check Security — match extensions or .env* filename patterns
    if ext in SECURITY_EXTENSIONS or ".env" in base:
        categories.add("security")
    for pattern in SECURITY_PATTERNS:
        if pattern in lower:
            categories.add("security")
            break

    # Check Docs
    for pattern in DOCS_PATTERNS:
        if pattern in lower:
            categories.add("docs")
            break

    # Check Tests
    for ext_pattern in TEST_EXTENSIONS:
        if lower.endswith(ext_pattern):
            categories.add("test")
            break

    # Check Config
    for pattern in CONFIG_PATTERNS:
        if pattern in lower:
            categories.add("config")
            break

    # If no category matched, it's general code
    if not categories:
        categories.add("code")

    return categories


def _categorize_feature(feature_description):
    """Categorize the feature description into change types."""
    categories = set()
    lower = feature_description.lower()

    for keyword in SECURITY_KEYWORDS:
        if keyword in lower:
            categories.add("security")
            break

    for keyword in UI_KEYWORDS:
        if keyword in lower:
            categories.add("ui")
            break

    for keyword in DOCS_KEYWORDS:
        if keyword in lower:
            categories.add("docs")
            break

    return categories


def select_agents(files_changed, feature_description=""):
    """Select which review agents to dispatch based on changed files and feature description.

    Returns a dict with:
        - agents: list of agent names to dispatch (always includes "dev")
        - reviewers: list of reviewer agent names (subset of agents, excludes dev)
        - reason: dict mapping each reviewer to why it was selected
        - skipped: dict mapping each skipped reviewer to why

    The pair principle: Dev is always included + at least 1 reviewer.
    """
    # Collect all file categories
    all_categories = set()
    file_categories = {}
    for f in files_changed:
        cats = _categorize_file(f)
        file_categories[f] = cats
        all_categories.update(cats)

    # Also consider feature description
    feature_cats = _categorize_feature(feature_description)
    all_categories.update(feature_cats)

    # Determine which reviewers are needed
    reviewers = {}
    skipped = {}

    # QA — always included if there are code changes (not just docs/config)
    code_changes = all_categories & {"code", "ui", "security", "test"}
    if code_changes:
        reviewers["qa"] = f"Code changes detected ({', '.join(sorted(code_changes))})"
    else:
        skipped["qa"] = "No code changes — only docs/config modified"

    # UI — only if UI-related files or feature description mentions UI
    if "ui" in all_categories:
        ui_files = [f for f, cats in file_categories.items() if "ui" in cats]
        reviewers["ui"] = f"UI files changed: {', '.join(ui_files[:5])}"
    else:
        skipped["ui"] = "No UI files changed and feature doesn't mention UI"

    # Security — only if security-related files/patterns or feature mentions security
    if "security" in all_categories:
        sec_files = [f for f, cats in file_categories.items() if "security" in cats]
        reason_parts = []
        if sec_files:
            reason_parts.append(f"Security-sensitive files: {', '.join(sec_files[:5])}")
        if "security" in feature_cats:
            reason_parts.append("Feature involves security-sensitive functionality")
        reviewers["security"] = "; ".join(reason_parts) if reason_parts else "Security patterns detected"
    else:
        skipped["security"] = "No security-sensitive files or patterns detected"

    # TPM — only if docs changed, config changed, or feature is architectural
    if all_categories & {"docs", "config"}:
        reviewers["tpm"] = "Documentation or configuration files changed"
    elif len(files_changed) > 10:
        reviewers["tpm"] = f"Large change ({len(files_changed)} files) — docs likely need updating"
    else:
        skipped["tpm"] = "No docs/config changes and change is small"

    # Enforce pair principle: minimum 1 reviewer
    if not reviewers:
        # Default to QA as the minimum reviewer
        reviewers["qa"] = "Pair principle: at least one reviewer required"
        if "qa" in skipped:
            del skipped["qa"]

    agents = ["dev"] + sorted(reviewers.keys())
    return {
        "agents": agents,
        "reviewers": sorted(reviewers.keys()),
        "reason": reviewers,
        "skipped": skipped,
    }


def render_selection(result):
    """Render agent selection as a markdown table."""
    lines = [
        "## Agent Selection",
        "",
        "| Agent | Status | Reason |",
        "|-------|--------|--------|",
        "| Dev | ACTIVE | Always active |",
    ]
    for agent in ["qa", "ui", "security", "tpm"]:
        if agent in result["reason"]:
            name = agent.upper() if agent in ("qa", "tpm") else agent.capitalize()
            lines.append(f"| {name} | ACTIVE | {result['reason'][agent]} |")
        elif agent in result["skipped"]:
            name = agent.upper() if agent in ("qa", "tpm") else agent.capitalize()
            lines.append(f"| {name} | SKIPPED | {result['skipped'][agent]} |")

    lines.append("")
    lines.append(f"> **{len(result['reviewers'])} reviewer(s) selected** (pair principle: minimum 1)")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 agent_selector.py '<files_json>' ['feature description']", file=sys.stderr)
        sys.exit(1)

    files = json.loads(sys.argv[1])
    feature = sys.argv[2] if len(sys.argv) > 2 else ""
    result = select_agents(files, feature)

    print(render_selection(result))
    print()
    print(json.dumps(result, indent=2))
