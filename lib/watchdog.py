"""Watchdog — monitors agent health: detects stalls, timeouts, and round completion."""

import argparse
import fcntl
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

REVIEWERS = ["qa", "ui", "security", "tpm"]


@dataclass
class WatchdogAlert:
    agent: str
    alert_type: str  # "STALLED" | "TIMEOUT"
    message: str
    idle_seconds: float = 0


def _sprint_dir(project_dir):
    return os.path.join(project_dir, ".sprint")


def _state_path(project_dir):
    return os.path.join(_sprint_dir(project_dir), "state.json")


def check_agents(project_dir, stall_threshold=180, agent_timeout=600):
    """Check all agents for stalls/timeouts and detect round completion.

    Returns a list of WatchdogAlert for any issues found.
    """
    state_path = _state_path(project_dir)

    # Read state under lock
    with open(str(state_path), "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            state = json.load(f)
            alerts = []
            now = datetime.now(timezone.utc)

            # Check each agent
            for agent_name, agent_info in state["agents"].items():
                status = agent_info.get("status")
                last_activity = agent_info.get("lastActivity")

                # Skip non-running agents
                if status != "running":
                    continue

                # Skip agents with no activity timestamp
                if last_activity is None:
                    continue

                last_dt = datetime.fromisoformat(last_activity)
                idle = (now - last_dt).total_seconds()

                if idle > agent_timeout:
                    # Timeout: update status in state
                    agent_info["status"] = "TIMEOUT"
                    alerts.append(WatchdogAlert(
                        agent=agent_name,
                        alert_type="TIMEOUT",
                        message=f"Agent {agent_name} timed out after {idle:.0f}s idle",
                        idle_seconds=idle,
                    ))
                elif idle > stall_threshold:
                    # Stalled: alert only, don't change status
                    alerts.append(WatchdogAlert(
                        agent=agent_name,
                        alert_type="STALLED",
                        message=f"Agent {agent_name} stalled: {idle:.0f}s idle",
                        idle_seconds=idle,
                    ))

            # Check round completion
            current_round = state.get("currentRound", 1)
            round_dir = os.path.join(
                _sprint_dir(project_dir), "rounds", f"round-{current_round}"
            )
            if os.path.isdir(round_dir):
                existing_reports = set(os.listdir(round_dir))
                required = {f"{r}-report.json" for r in REVIEWERS}
                if required.issubset(existing_reports):
                    state["phase"] = "consensus_ready"

            # Write state back
            f.seek(0)
            f.truncate()
            json.dump(state, f, indent=2)

            return alerts
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def run_loop(project_dir, interval=30, stall_threshold=180, agent_timeout=600):
    """Infinite loop: check agents every `interval` seconds, print alerts to stderr."""
    while True:
        try:
            alerts = check_agents(project_dir, stall_threshold, agent_timeout)
            for alert in alerts:
                print(
                    f"[WATCHDOG] {alert.alert_type}: {alert.message}",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"[WATCHDOG] Error: {exc}", file=sys.stderr)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sprint watchdog")
    parser.add_argument("project_dir", help="Path to the project directory")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="Run once and exit")
    group.add_argument("--loop", action="store_true", help="Run in continuous loop")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.project_dir)
    else:
        alerts = check_agents(args.project_dir)
        for alert in alerts:
            print(f"[WATCHDOG] {alert.alert_type}: {alert.message}", file=sys.stderr)
