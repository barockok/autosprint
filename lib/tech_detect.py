"""Tech stack auto-detection module.

Scans a project directory for configuration files and determines which
technology stacks are in use.  Returns a dict suitable for driving the
sprint multi-agent system.

Usage as a library:
    from lib.tech_detect import detect_tech_stack
    result = detect_tech_stack("/path/to/project")

Usage as CLI:
    python -m lib.tech_detect [directory]
"""

import json
import os
import sys


# ---------------------------------------------------------------------------
# Detection rule definitions
# ---------------------------------------------------------------------------

# Each rule is a tuple:
#   (check_fn, stack_id, qa_tool, ui_validation, security_focus_list)
# check_fn receives (project_dir, package_json_deps) where package_json_deps
# is the merged set of dependency names (dependencies + devDependencies) or
# None when package.json is absent.

_FRONTEND_PACKAGES = {"react", "vue", "svelte", "@angular/core", "angular"}
_BACKEND_PACKAGES = {"express", "fastify", "hono", "next", "@nestjs/core"}


def _has_frontend(project_dir, deps):
    return deps is not None and bool(deps & _FRONTEND_PACKAGES)


def _has_backend(project_dir, deps):
    return deps is not None and bool(deps & _BACKEND_PACKAGES)


def _has_electron(project_dir, deps):
    return deps is not None and "electron" in deps


def _has_tauri(project_dir, deps):
    cargo = os.path.join(project_dir, "Cargo.toml")
    if not os.path.isfile(cargo):
        return False
    try:
        with open(cargo, "r") as f:
            content = f.read()
    except OSError:
        return False
    return "tauri" in content


def _has_ios(project_dir, deps):
    if os.path.isfile(os.path.join(project_dir, "Podfile")):
        return True
    # Check for *.xcodeproj directories
    try:
        entries = os.listdir(project_dir)
    except OSError:
        return False
    for entry in entries:
        if entry.endswith(".xcodeproj"):
            return True
    return False


def _has_android(project_dir, deps):
    return (
        os.path.isfile(os.path.join(project_dir, "build.gradle"))
        or os.path.isfile(os.path.join(project_dir, "build.gradle.kts"))
        or os.path.isfile(os.path.join(project_dir, "AndroidManifest.xml"))
    )


def _has_flutter(project_dir, deps):
    return os.path.isfile(os.path.join(project_dir, "pubspec.yaml"))


def _has_rust_cli(project_dir, deps):
    cargo = os.path.join(project_dir, "Cargo.toml")
    if not os.path.isfile(cargo):
        return False
    # Rust CLI only if tauri is NOT present
    try:
        with open(cargo, "r") as f:
            content = f.read()
    except OSError:
        return False
    return "tauri" not in content


def _has_go(project_dir, deps):
    return os.path.isfile(os.path.join(project_dir, "go.mod"))


def _has_python(project_dir, deps):
    return (
        os.path.isfile(os.path.join(project_dir, "pyproject.toml"))
        or os.path.isfile(os.path.join(project_dir, "setup.py"))
    )


RULES = [
    (_has_frontend, "web-frontend", "playwright", "browser-automation",
     ["XSS", "CSP", "CORS"]),
    (_has_backend, "web-backend", "supertest", "none",
     ["SQLi", "auth", "IDOR"]),
    (_has_electron, "desktop-electron", "playwright", "window-automation",
     ["node-integration", "IPC"]),
    (_has_tauri, "desktop-tauri", "playwright", "window-automation",
     ["IPC", "command-injection"]),
    (_has_ios, "ios", "xctest", "simulator",
     ["keychain", "ATS", "data-leaks"]),
    (_has_android, "android", "maestro", "emulator",
     ["intent-injection", "storage"]),
    (_has_flutter, "mobile-cross-platform", "maestro", "simulator",
     ["platform-specific"]),
    (_has_rust_cli, "cli-rust", "shell-e2e", "none",
     ["input-validation", "path-traversal"]),
    (_has_go, "cli-go", "shell-e2e", "none",
     ["input-validation", "path-traversal"]),
    (_has_python, "python", "pytest", "none",
     ["dependency-audit", "injection"]),
]


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def _load_package_json_deps(project_dir):
    """Return the merged set of dependency names from package.json, or None."""
    pj_path = os.path.join(project_dir, "package.json")
    if not os.path.isfile(pj_path):
        return None
    try:
        with open(pj_path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    deps = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            deps.update(section.keys())
    return deps


def detect_tech_stack(project_dir):
    """Detect technology stacks used in *project_dir*.

    Returns a dict with keys:
        stacks          - list of matched stack IDs
        qa_tool         - primary QA tool (from first match)
        ui_validation   - primary UI validation strategy (from first match)
        security_focus  - deduplicated list of security concerns
    """
    project_dir = os.path.abspath(project_dir)
    deps = _load_package_json_deps(project_dir)

    stacks = []
    qa_tool = None
    ui_validation = None
    security_items = []

    for check_fn, stack_id, rule_qa, rule_ui, rule_sec in RULES:
        if check_fn(project_dir, deps):
            stacks.append(stack_id)
            if qa_tool is None:
                qa_tool = rule_qa
                ui_validation = rule_ui
            for item in rule_sec:
                if item not in security_items:
                    security_items.append(item)

    if not stacks:
        return {
            "stacks": ["generic"],
            "qa_tool": "shell-e2e",
            "ui_validation": "none",
            "security_focus": ["general"],
        }

    return {
        "stacks": stacks,
        "qa_tool": qa_tool,
        "ui_validation": ui_validation,
        "security_focus": security_items,
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    result = detect_tech_stack(directory)
    print(json.dumps(result, indent=2))
