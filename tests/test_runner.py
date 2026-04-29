from codex_monitor.config import (
    ActorFilterConfig,
    CodexMonitorConfig,
    DeliveryConfig,
    EventConfig,
    GitLabConfig,
    MonitorConfig,
)
from codex_monitor.render import MonitorEvent
from codex_monitor.runner import run_once


def _config(tmp_path):
    return CodexMonitorConfig(
        monitor=MonitorConfig("test-monitor", "gitlab"),
        gitlab=GitLabConfig("gitlab.example.test", "", ("group/project",), True),
        events=EventConfig(),
        actor_filter=ActorFilterConfig(),
        delivery=DeliveryConfig(
            tmux_target="agent",
            dry_run=False,
            state_path=tmp_path / "state.json",
            log_path=tmp_path / "monitor.log",
        ),
    )


def test_run_once_primes_state_without_replaying(monkeypatch, tmp_path):
    events = [
        MonitorEvent("merge_requests", "event-1", "merge_request.opened", "group/project", "url", "actor", "title")
    ]
    monkeypatch.setattr("codex_monitor.monitors.gitlab.GitLabMonitor.fetch_events", lambda self: events)

    count = run_once(_config(tmp_path), dry_run=True)

    assert count == 0
    assert "event-1" in (tmp_path / "state.json").read_text(encoding="utf-8")


def test_run_once_queues_when_tmux_not_idle(monkeypatch, tmp_path):
    first = [
        MonitorEvent("merge_requests", "event-1", "merge_request.opened", "group/project", "url", "actor", "title")
    ]
    second = first + [
        MonitorEvent("merge_requests", "event-2", "merge_request.opened", "group/project", "url", "actor", "title")
    ]
    calls = iter([first, second])
    monkeypatch.setattr("codex_monitor.monitors.gitlab.GitLabMonitor.fetch_events", lambda self: next(calls))
    monkeypatch.setattr(
        "codex_monitor.tmux_delivery.TmuxDelivery.deliver",
        lambda self, message, idle_check=True, dry_run=False: type("R", (), {"outcome": "queued_not_idle", "success": False})(),
    )
    config = _config(tmp_path)

    run_once(config)
    count = run_once(config)

    assert count == 1
    assert "pending_wake_messages" in (tmp_path / "state.json").read_text(encoding="utf-8")
    assert "event-2" in (tmp_path / "state.json").read_text(encoding="utf-8")
