"""Tests for lib/watchdog.py — watchdog agent health monitoring."""

import json
import os
from datetime import datetime, timezone, timedelta

import pytest

from lib.state_manager import init_sprint, update_agent_status, get_state
from lib.watchdog import check_agents, WatchdogAlert


@pytest.fixture
def sprint_dir(tmp_path):
    """Initialize a sprint project in a temp directory."""
    init_sprint(tmp_path, "test-feature", "python", max_rounds=3)
    return tmp_path


def _backdate_agent(project_dir, agent, seconds_ago):
    """Helper: backdate an agent's lastActivity by N seconds."""
    state_path = os.path.join(project_dir, ".sprint", "state.json")
    state = json.loads(open(state_path).read())
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    state["agents"][agent]["lastActivity"] = old_time
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def test_no_alerts_for_pending_agents(sprint_dir):
    """All agents are pending by default — no alerts should fire."""
    alerts = check_agents(sprint_dir)
    assert alerts == []


def test_no_alerts_for_recent_activity(sprint_dir):
    """A running agent with recent activity should not trigger alerts."""
    update_agent_status(sprint_dir, "dev", "running")
    alerts = check_agents(sprint_dir)
    assert alerts == []


def test_stall_alert_for_old_activity(sprint_dir):
    """A running agent idle > stall_threshold should get a STALLED alert."""
    update_agent_status(sprint_dir, "dev", "running")
    _backdate_agent(sprint_dir, "dev", 200)  # 200s > 180s threshold

    alerts = check_agents(sprint_dir)
    assert len(alerts) == 1
    assert alerts[0].agent == "dev"
    assert alerts[0].alert_type == "STALLED"
    assert alerts[0].idle_seconds >= 200


def test_timeout_alert(sprint_dir):
    """A running agent idle > agent_timeout should get a TIMEOUT alert."""
    update_agent_status(sprint_dir, "dev", "running")
    _backdate_agent(sprint_dir, "dev", 700)  # 700s > 600s timeout

    alerts = check_agents(sprint_dir)
    assert len(alerts) == 1
    assert alerts[0].agent == "dev"
    assert alerts[0].alert_type == "TIMEOUT"
    assert alerts[0].idle_seconds >= 700


def test_timeout_updates_state(sprint_dir):
    """After a timeout alert, the agent status in state.json should be TIMEOUT."""
    update_agent_status(sprint_dir, "dev", "running")
    _backdate_agent(sprint_dir, "dev", 700)

    check_agents(sprint_dir)
    state = get_state(sprint_dir)
    assert state["agents"]["dev"]["status"] == "TIMEOUT"


def test_completed_agents_ignored(sprint_dir):
    """Completed agents with old timestamps should not trigger alerts."""
    update_agent_status(sprint_dir, "dev", "completed")
    _backdate_agent(sprint_dir, "dev", 9999)

    alerts = check_agents(sprint_dir)
    assert alerts == []


def test_round_completion_detection(sprint_dir):
    """When all 4 reviewer reports exist in round dir, phase becomes consensus_ready."""
    reviewers = ["qa", "ui", "security", "tpm"]
    round_dir = os.path.join(sprint_dir, ".sprint", "rounds", "round-1")
    os.makedirs(round_dir, exist_ok=True)

    for reviewer in reviewers:
        report_path = os.path.join(round_dir, f"{reviewer}-report.json")
        with open(report_path, "w") as f:
            json.dump({"agent": reviewer, "vote": "PASS", "summary": "ok"}, f)

    check_agents(sprint_dir)
    state = get_state(sprint_dir)
    assert state["phase"] == "consensus_ready"
