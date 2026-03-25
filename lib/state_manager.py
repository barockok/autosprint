"""State Manager — manages .autosprint/ directory lifecycle, agent status, consensus, and kanban rendering."""

import fcntl
import json
import os
import sys
from datetime import datetime, timezone

AGENTS = ["dev", "qa", "ui", "security", "tpm"]
REVIEWERS = ["qa", "ui", "security", "tpm"]
VALID_STATUSES = {"pending", "running", "completed", "TIMEOUT"}
VALID_VOTES = {"PASS", "FAIL", "OVERRIDE"}

AGENT_DISPLAY = {
    "dev": "Dev",
    "qa": "QA",
    "ui": "UI",
    "security": "Security",
    "tpm": "TPM",
}


def _sprint_dir(project_dir):
    return os.path.join(project_dir, ".autosprint")


def _state_path(project_dir):
    return os.path.join(_sprint_dir(project_dir), "state.json")


def _config_path(project_dir):
    return os.path.join(_sprint_dir(project_dir), "config.json")


def _read_json(path):
    with open(path) as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _locked_update(project_dir, mutator_fn):
    """Read state.json, apply mutator_fn, write back — all under exclusive file lock."""
    path = _state_path(project_dir)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"state.json not found at {path}. Run init_sprint() first."
        )
    with open(str(path), "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            data = json.load(f)
            mutator_fn(data)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def init_sprint(project_dir, feature, tech_stack, max_rounds=3, slices=None):
    """Initialize .autosprint/ directory with state and config."""
    if slices is None:
        slices = [feature]

    sprint = _sprint_dir(project_dir)
    os.makedirs(os.path.join(sprint, "rounds"), exist_ok=True)
    os.makedirs(os.path.join(sprint, "logs"), exist_ok=True)

    agents = {}
    for agent in AGENTS:
        agents[agent] = {
            "status": "pending",
            "lastActivity": None,
            "worktree": None,
        }

    state = {
        "feature": feature,
        "techStack": tech_stack,
        "currentSlice": 1,
        "totalSlices": len(slices),
        "currentRound": 1,
        "maxRounds": max_rounds,
        "phase": "setup",
        "agents": agents,
        "consensus": {},
    }
    _write_json(_state_path(project_dir), state)

    config = {
        "feature": feature,
        "techStack": tech_stack,
        "maxRounds": max_rounds,
        "slices": slices,
        "stallThreshold": 180,
        "agentTimeout": 600,
    }
    _write_json(_config_path(project_dir), config)

    # Add .autosprint/ to .gitignore
    gitignore_path = os.path.join(project_dir, ".gitignore")
    entry = ".autosprint/"
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if entry not in content.splitlines():
            with open(gitignore_path, "a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(entry + "\n")
    else:
        with open(gitignore_path, "w") as f:
            f.write(entry + "\n")


def get_state(project_dir):
    """Read and return state.json as dict."""
    path = _state_path(project_dir)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"state.json not found at {path}. Run init_sprint() first."
        )
    return _read_json(path)


def update_agent_status(project_dir, agent, status, phase=None):
    """Update agent status and lastActivity timestamp."""
    if agent not in AGENTS:
        raise ValueError(f"Unknown agent: {agent}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    def _mutate(data):
        data["agents"][agent]["status"] = status
        data["agents"][agent]["lastActivity"] = datetime.now(timezone.utc).isoformat()
        if phase is not None:
            data["phase"] = phase

    _locked_update(project_dir, _mutate)


def record_vote(project_dir, round_num, agent, vote, summary):
    """Record a vote in state.json and write a report file."""
    if agent not in AGENTS:
        raise ValueError(f"Unknown agent: {agent}")
    if vote not in VALID_VOTES:
        raise ValueError(f"Invalid vote: {vote}")

    round_key = f"round-{round_num}"

    def _mutate(data):
        if round_key not in data["consensus"]:
            data["consensus"][round_key] = {}
        data["consensus"][round_key][agent] = {
            "vote": vote,
            "summary": summary,
        }

    _locked_update(project_dir, _mutate)

    # Write report file
    round_dir = os.path.join(_sprint_dir(project_dir), "rounds", round_key)
    os.makedirs(round_dir, exist_ok=True)
    report = {
        "agent": agent,
        "vote": vote,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    report_path = os.path.join(round_dir, f"{agent}-report.json")
    _write_json(report_path, report)


def check_consensus(project_dir, round_num):
    """Check consensus for a round. Returns APPROVED, REJECTED, or PENDING."""
    state = get_state(project_dir)
    round_key = f"round-{round_num}"
    votes = state["consensus"].get(round_key, {})

    # Check if all reviewers have voted
    if not all(r in votes for r in REVIEWERS):
        return "PENDING"

    # Check for OVERRIDE
    if any(votes[r]["vote"] == "OVERRIDE" for r in REVIEWERS):
        return "APPROVED"

    # Check for any FAIL
    if any(votes[r]["vote"] == "FAIL" for r in REVIEWERS):
        return "REJECTED"

    # All PASS
    return "APPROVED"


def render_kanban(project_dir, fmt="markdown"):
    """Render agent status as kanban board."""
    state = get_state(project_dir)

    if fmt == "json":
        return {
            "feature": state["feature"],
            "currentSlice": state["currentSlice"],
            "totalSlices": state["totalSlices"],
            "currentRound": state["currentRound"],
            "maxRounds": state["maxRounds"],
            "agents": state["agents"],
        }

    # Markdown GFM table
    lines = []
    lines.append(f"## AutoSprint: {state['feature']}")
    lines.append("")
    lines.append(
        f"**Slice {state['currentSlice']}/{state['totalSlices']}"
        f" | Round {state['currentRound']}/{state['maxRounds']}**"
    )
    lines.append("")
    lines.append("| Agent | Pending | Running | Completed | Verdict |")
    lines.append("| --- | --- | --- | --- | --- |")

    counts = {"pending": 0, "running": 0, "completed": 0}
    for agent in AGENTS:
        info = state["agents"][agent]
        status = info["status"]
        display = AGENT_DISPLAY[agent]
        pending = "x" if status == "pending" else ""
        running = "x" if status == "running" else ""
        completed = "x" if status == "completed" else ""
        verdict = ""
        # Count
        if status in counts:
            counts[status] += 1
        lines.append(f"| {display} | {pending} | {running} | {completed} | {verdict} |")

    lines.append("")
    total = len(AGENTS)
    done_count = counts["completed"]
    lines.append(f"Progress: {done_count}/{total} agents complete")

    return "\n".join(lines)


def render_consensus(project_dir, round_num):
    """Render consensus table for a round."""
    state = get_state(project_dir)
    round_key = f"round-{round_num}"
    votes = state["consensus"].get(round_key, {})

    lines = []
    lines.append(f"## Consensus: Round {round_num}")
    lines.append("")
    lines.append("| Agent | Vote | Summary |")
    lines.append("| --- | --- | --- |")

    for agent in REVIEWERS:
        display = AGENT_DISPLAY[agent]
        if agent in votes:
            v = votes[agent]
            lines.append(f"| {display} | {v['vote']} | {v['summary']} |")
        else:
            lines.append(f"| {display} | - | - |")

    result = check_consensus(project_dir, round_num)
    lines.append("")
    lines.append(f"**Result: {result}**")

    return "\n".join(lines)


def render_overview(project_dir):
    """Render all-slices overview table."""
    state = get_state(project_dir)
    config = _read_json(_config_path(project_dir))
    slices = config.get("slices", [])

    lines = []
    lines.append(f"## Overview: {state['feature']}")
    lines.append("")
    lines.append("| Slice | Status | Rounds | Agents | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")

    for i, slice_name in enumerate(slices, 1):
        if i < state["currentSlice"]:
            status = "done"
        elif i == state["currentSlice"]:
            status = state["phase"]
        else:
            status = "pending"

        current_round = state["currentRound"] if i == state["currentSlice"] else "-"
        max_rounds = state["maxRounds"]
        rounds_str = f"{current_round}/{max_rounds}" if current_round != "-" else "-"

        # Count active agents for current slice
        if i == state["currentSlice"]:
            active = sum(
                1 for a in AGENTS if state["agents"][a]["status"] == "running"
            )
            agents_str = f"{active}/{len(AGENTS)}"
        else:
            agents_str = "-"

        lines.append(f"| {slice_name} | {status} | {rounds_str} | {agents_str} | |")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 lib/state_manager.py <project_dir> [kanban|consensus|overview]")
        sys.exit(1)

    proj = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else "kanban"

    if cmd == "kanban":
        print(render_kanban(proj))
    elif cmd == "consensus":
        state = get_state(proj)
        round_num = state["currentRound"]
        print(render_consensus(proj, round_num))
    elif cmd == "overview":
        print(render_overview(proj))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
