"""Tests for lib/state_manager.py — State Manager with kanban rendering."""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from lib import state_manager
from lib.state_manager import (
    AGENTS,
    REVIEWERS,
    VALID_VOTES,
    _locked_update,
    check_consensus,
    get_state,
    init_sprint,
    record_vote,
    render_consensus,
    render_kanban,
    render_overview,
    update_agent_status,
)


@pytest.fixture
def project(tmp_path):
    """Create a temporary project directory."""
    return str(tmp_path)


@pytest.fixture
def initialized_project(project):
    """Create and initialize a sprint project."""
    init_sprint(project, "dark mode", "React, TailwindCSS", max_rounds=3, slices=["UI theme", "toggle component"])
    return project


class TestInitSprint:
    def test_creates_sprint_directory(self, project):
        init_sprint(project, "dark mode", "React, TailwindCSS")
        sprint_dir = os.path.join(project, ".sprint")
        assert os.path.isdir(sprint_dir)
        assert os.path.isdir(os.path.join(sprint_dir, "rounds"))
        assert os.path.isdir(os.path.join(sprint_dir, "logs"))

    def test_state_json_structure(self, project):
        init_sprint(project, "dark mode", "React, TailwindCSS", max_rounds=3, slices=["UI theme", "toggle"])
        state = get_state(project)
        assert state["feature"] == "dark mode"
        assert state["techStack"] == "React, TailwindCSS"
        assert state["currentSlice"] == 1
        assert state["totalSlices"] == 2
        assert state["currentRound"] == 1
        assert state["maxRounds"] == 3
        assert state["phase"] == "setup"
        assert state["consensus"] == {}
        # Check all agents exist with correct structure
        for agent in AGENTS:
            assert agent in state["agents"]
            assert state["agents"][agent]["status"] == "pending"
            assert state["agents"][agent]["lastActivity"] is None
            assert state["agents"][agent]["worktree"] is None

    def test_adds_gitignore(self, project):
        init_sprint(project, "dark mode", "React")
        gitignore_path = os.path.join(project, ".gitignore")
        assert os.path.isfile(gitignore_path)
        with open(gitignore_path) as f:
            content = f.read()
        assert ".sprint/" in content

    def test_appends_gitignore_if_exists(self, project):
        gitignore_path = os.path.join(project, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("node_modules/\n")
        init_sprint(project, "dark mode", "React")
        with open(gitignore_path) as f:
            content = f.read()
        assert "node_modules/" in content
        assert ".sprint/" in content


class TestUpdateAgentStatus:
    def test_updates_status_and_last_activity(self, initialized_project):
        before = datetime.now(timezone.utc)
        update_agent_status(initialized_project, "dev", "running")
        state = get_state(initialized_project)
        assert state["agents"]["dev"]["status"] == "running"
        ts = datetime.fromisoformat(state["agents"]["dev"]["lastActivity"])
        assert ts >= before

    def test_updates_phase(self, initialized_project):
        update_agent_status(initialized_project, "dev", "running", phase="development")
        state = get_state(initialized_project)
        assert state["phase"] == "development"


class TestConsensus:
    def test_record_vote_pass(self, initialized_project):
        record_vote(initialized_project, 1, "qa", "PASS", "All tests pass")
        state = get_state(initialized_project)
        assert "round-1" in state["consensus"]
        assert state["consensus"]["round-1"]["qa"]["vote"] == "PASS"
        assert state["consensus"]["round-1"]["qa"]["summary"] == "All tests pass"

    def test_record_vote_fail(self, initialized_project):
        record_vote(initialized_project, 1, "security", "FAIL", "XSS vulnerability found")
        state = get_state(initialized_project)
        assert state["consensus"]["round-1"]["security"]["vote"] == "FAIL"
        assert state["consensus"]["round-1"]["security"]["summary"] == "XSS vulnerability found"

    def test_consensus_all_pass(self, initialized_project):
        for agent in REVIEWERS:
            record_vote(initialized_project, 1, agent, "PASS", "Looks good")
        result = check_consensus(initialized_project, 1)
        assert result == "APPROVED"

    def test_consensus_any_fail(self, initialized_project):
        record_vote(initialized_project, 1, "qa", "PASS", "OK")
        record_vote(initialized_project, 1, "ui", "PASS", "OK")
        record_vote(initialized_project, 1, "security", "FAIL", "Bad")
        record_vote(initialized_project, 1, "tpm", "PASS", "OK")
        result = check_consensus(initialized_project, 1)
        assert result == "REJECTED"

    def test_consensus_tpm_override(self, initialized_project):
        record_vote(initialized_project, 1, "qa", "PASS", "OK")
        record_vote(initialized_project, 1, "ui", "PASS", "OK")
        record_vote(initialized_project, 1, "security", "FAIL", "Bad")
        record_vote(initialized_project, 1, "tpm", "OVERRIDE", "Overriding security concern")
        result = check_consensus(initialized_project, 1)
        assert result == "APPROVED"

    def test_consensus_incomplete(self, initialized_project):
        record_vote(initialized_project, 1, "qa", "PASS", "OK")
        result = check_consensus(initialized_project, 1)
        assert result == "PENDING"

    def test_record_vote_creates_report_file(self, initialized_project):
        record_vote(initialized_project, 1, "qa", "PASS", "All tests pass")
        report_path = os.path.join(
            initialized_project, ".sprint", "rounds", "round-1", "qa-report.json"
        )
        assert os.path.isfile(report_path)
        with open(report_path) as f:
            report = json.load(f)
        assert report["vote"] == "PASS"
        assert report["summary"] == "All tests pass"


class TestKanbanRendering:
    def test_render_kanban_markdown(self, initialized_project):
        update_agent_status(initialized_project, "dev", "running")
        update_agent_status(initialized_project, "qa", "completed")
        output = render_kanban(initialized_project, fmt="markdown")
        assert "## Sprint: dark mode" in output
        assert "Slice 1/2 | Round 1/3" in output
        assert "Agent" in output
        assert "Dev" in output
        assert "QA" in output
        assert "UI" in output
        assert "Security" in output
        assert "TPM" in output
        # Check it's a GFM table (has pipes and dashes)
        assert "|" in output
        assert "---" in output

    def test_render_consensus_markdown(self, initialized_project):
        for agent in REVIEWERS:
            record_vote(initialized_project, 1, agent, "PASS", "Looks good")
        output = render_consensus(initialized_project, 1)
        assert "Agent" in output
        assert "Vote" in output
        assert "Summary" in output
        assert "PASS" in output
        assert "APPROVED" in output

    def test_render_overview_markdown(self, initialized_project):
        output = render_overview(initialized_project)
        assert "Slice" in output
        assert "Status" in output
        assert "|" in output

    def test_render_kanban_json(self, initialized_project):
        update_agent_status(initialized_project, "dev", "running")
        result = render_kanban(initialized_project, fmt="json")
        assert isinstance(result, dict)
        assert "feature" in result
        assert "agents" in result


class TestInputValidation:
    def test_update_agent_status_invalid_agent(self, initialized_project):
        with pytest.raises(ValueError, match="Unknown agent: hacker"):
            update_agent_status(initialized_project, "hacker", "running")

    def test_record_vote_invalid_agent(self, initialized_project):
        with pytest.raises(ValueError, match="Unknown agent: hacker"):
            record_vote(initialized_project, 1, "hacker", "PASS", "ok")

    def test_record_vote_invalid_vote(self, initialized_project):
        with pytest.raises(ValueError, match="Invalid vote: MAYBE"):
            record_vote(initialized_project, 1, "qa", "MAYBE", "ok")

    def test_get_state_missing_file(self, project):
        with pytest.raises(FileNotFoundError, match="state.json not found"):
            get_state(project)


class TestFileLocking:
    def test_locked_update_smoke(self, initialized_project):
        """Basic smoke test: _locked_update reads, mutates, and writes back correctly."""
        def _set_phase(data):
            data["phase"] = "review"

        _locked_update(initialized_project, _set_phase)
        state = get_state(initialized_project)
        assert state["phase"] == "review"

    def test_locked_update_preserves_data(self, initialized_project):
        """Ensure _locked_update does not lose existing data."""
        update_agent_status(initialized_project, "dev", "running")

        def _set_phase(data):
            data["phase"] = "consensus"

        _locked_update(initialized_project, _set_phase)
        state = get_state(initialized_project)
        assert state["phase"] == "consensus"
        assert state["agents"]["dev"]["status"] == "running"
