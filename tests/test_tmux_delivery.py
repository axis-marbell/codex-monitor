import subprocess
from unittest.mock import Mock

from codex_monitor.tmux_delivery import TmuxDelivery


def test_delivery_queues_when_not_idle(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["tmux", "has-session"]:
            return subprocess.CompletedProcess(args, 0)
        if args[:2] == ["tmux", "capture-pane"]:
            return subprocess.CompletedProcess(args, 0, stdout="running command\n")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("codex_monitor.tmux_delivery.tmux_available", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = TmuxDelivery("agent").deliver("wake", idle_check=True)

    assert result.outcome == "queued_not_idle"
    assert not any(call[:2] == ["tmux", "send-keys"] for call in calls)


def test_delivery_uses_two_send_keys_calls(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["tmux", "has-session"]:
            return subprocess.CompletedProcess(args, 0)
        if args[:2] == ["tmux", "capture-pane"]:
            return subprocess.CompletedProcess(args, 0, stdout="$ \n")
        if args[:2] == ["tmux", "send-keys"]:
            return subprocess.CompletedProcess(args, 0)
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("codex_monitor.tmux_delivery.tmux_available", lambda: True)
    monkeypatch.setattr("time.sleep", Mock())
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = TmuxDelivery("agent").deliver("wake", idle_check=True)

    assert result.outcome == "delivered"
    send_calls = [call for call in calls if call[:2] == ["tmux", "send-keys"]]
    assert send_calls == [
        ["tmux", "send-keys", "-t", "agent", "wake"],
        ["tmux", "send-keys", "-t", "agent", "Enter"],
    ]
