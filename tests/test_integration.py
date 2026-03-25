"""Integration tests — full sprint lifecycle exercising tech_detect, state_manager, and watchdog together."""

import json
import os

import pytest

from lib.tech_detect import detect_tech_stack
from lib.state_manager import (
    init_sprint,
    update_agent_status,
    record_vote,
    check_consensus,
    render_kanban,
    render_consensus,
    render_overview,
    get_state,
)
from lib.watchdog import check_agents


# ---------------------------------------------------------------------------
# test_complete_sprint_lifecycle
# ---------------------------------------------------------------------------

def test_complete_sprint_lifecycle(tmp_path):
    """Full happy-path lifecycle: detect -> init -> dev -> review -> approve."""
    # 1. Create a fake React project
    package_json = {
        "name": "my-app",
        "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(package_json))

    # 2. Detect tech stack
    tech = detect_tech_stack(str(tmp_path))
    assert "web-frontend" in tech["stacks"]

    # 3. Init sprint with 2 slices
    slices = ["login-page", "dashboard"]
    init_sprint(
        str(tmp_path),
        feature="user-auth",
        tech_stack=tech,
        slices=slices,
    )
    state = get_state(str(tmp_path))
    assert state["totalSlices"] == 2
    assert state["feature"] == "user-auth"

    # 4. Dev starts then completes
    update_agent_status(str(tmp_path), "dev", "running", phase="dev")
    update_agent_status(str(tmp_path), "dev", "completed")

    # 5. Render kanban — assert "Dev" and status visible
    kanban = render_kanban(str(tmp_path))
    assert "Dev" in kanban
    assert "completed" in kanban.lower() or "x" in kanban

    # 6. All 4 reviewers vote PASS
    for agent in ["qa", "ui", "security", "tpm"]:
        record_vote(str(tmp_path), round_num=1, agent=agent, vote="PASS", summary="All good")

    # 7. Check consensus — APPROVED
    result = check_consensus(str(tmp_path), round_num=1)
    assert result == "APPROVED"

    # 8. Render consensus — contains PASS and APPROVED
    consensus_md = render_consensus(str(tmp_path), round_num=1)
    assert "PASS" in consensus_md
    assert "APPROVED" in consensus_md

    # 9. Render overview — both slice names present
    overview = render_overview(str(tmp_path))
    assert "login-page" in overview
    assert "dashboard" in overview

    # 10. Watchdog check — no alerts
    alerts = check_agents(str(tmp_path))
    assert alerts == []


# ---------------------------------------------------------------------------
# test_rejected_round_lifecycle
# ---------------------------------------------------------------------------

def test_rejected_round_lifecycle(tmp_path):
    """Lifecycle where security rejects the round."""
    # 1. Create an Express project
    package_json = {
        "name": "api-server",
        "dependencies": {"express": "^4.18.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(package_json))

    # 2. Detect tech stack and init sprint
    tech = detect_tech_stack(str(tmp_path))
    assert "web-backend" in tech["stacks"]

    init_sprint(
        str(tmp_path),
        feature="api-endpoints",
        tech_stack=tech,
        slices=["users-endpoint"],
    )

    # 3. Dev completes
    update_agent_status(str(tmp_path), "dev", "running", phase="dev")
    update_agent_status(str(tmp_path), "dev", "completed")

    # 4. Three agents PASS, security votes FAIL with "SQL injection"
    record_vote(str(tmp_path), 1, "qa", "PASS", "Tests pass")
    record_vote(str(tmp_path), 1, "ui", "PASS", "N/A for backend")
    record_vote(str(tmp_path), 1, "tpm", "PASS", "Looks good")
    record_vote(str(tmp_path), 1, "security", "FAIL", "SQL injection found in query builder")

    # 5. Check consensus — REJECTED
    result = check_consensus(str(tmp_path), round_num=1)
    assert result == "REJECTED"

    # 6. Render consensus — shows FAIL and REJECTED
    consensus_md = render_consensus(str(tmp_path), round_num=1)
    assert "FAIL" in consensus_md
    assert "REJECTED" in consensus_md


# ---------------------------------------------------------------------------
# test_tpm_override_lifecycle
# ---------------------------------------------------------------------------

def test_tpm_override_lifecycle(tmp_path):
    """Lifecycle where TPM overrides a UI FAIL to approve the round."""
    # 1. Init sprint (generic project)
    tech = {"stacks": ["generic"], "qa_tool": "shell-e2e", "ui_validation": "none", "security_focus": ["general"]}
    init_sprint(
        str(tmp_path),
        feature="quick-fix",
        tech_stack=tech,
        slices=["hotfix"],
    )

    # 2. Dev completes
    update_agent_status(str(tmp_path), "dev", "running", phase="dev")
    update_agent_status(str(tmp_path), "dev", "completed")

    # 3. QA PASS, UI FAIL with minor issue, Security PASS, TPM votes OVERRIDE
    record_vote(str(tmp_path), 1, "qa", "PASS", "All tests green")
    record_vote(str(tmp_path), 1, "ui", "FAIL", "Minor alignment issue")
    record_vote(str(tmp_path), 1, "security", "PASS", "No issues found")
    record_vote(str(tmp_path), 1, "tpm", "OVERRIDE", "Accepting minor UI issue for release")

    # 4. Check consensus — APPROVED (override wins)
    result = check_consensus(str(tmp_path), round_num=1)
    assert result == "APPROVED"
