"""Tmux wake delivery for Codex agents."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass


PROMPT_SUFFIXES = ("$ ", "> ", "% ", "# ", "❯ ", "➜ ")


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    outcome: str
    reason: str = ""


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


def detect_current_target() -> str:
    """Return the current tmux target as session:window.pane."""
    if not tmux_available():
        return ""
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S:#I.#P"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


class TmuxDelivery:
    """Deliver wake messages using tmux send-keys."""

    def __init__(self, target: str, send_delay_seconds: float = 1.0) -> None:
        self.target = target
        self.send_delay_seconds = send_delay_seconds

    def session_exists(self) -> bool:
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self.target],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def looks_idle(self) -> bool:
        """Conservative prompt check using the last captured pane line."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-p", "-t", self.target],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
            return False
        lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return False
        last = lines[-1]
        return any(last.endswith(suffix.rstrip()) or last.endswith(suffix) for suffix in PROMPT_SUFFIXES)

    def deliver(self, message: str, *, idle_check: bool = False, dry_run: bool = False) -> DeliveryResult:
        if dry_run:
            return DeliveryResult(True, "dry_run")
        if not tmux_available():
            return DeliveryResult(False, "skipped_no_tmux", "tmux binary not found")
        if not self.target:
            return DeliveryResult(False, "skipped_no_target", "tmux target is empty")
        if not self.session_exists():
            return DeliveryResult(False, "skipped_no_session", f"tmux target not found: {self.target}")
        if idle_check and not self.looks_idle():
            return DeliveryResult(False, "queued_not_idle", "tmux pane does not look idle")
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", self.target, message],
                check=True,
                capture_output=True,
                timeout=10,
            )
            time.sleep(self.send_delay_seconds)
            subprocess.run(
                ["tmux", "send-keys", "-t", self.target, "Enter"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as exc:
            return DeliveryResult(False, "failed", str(exc))
        return DeliveryResult(True, "delivered")
