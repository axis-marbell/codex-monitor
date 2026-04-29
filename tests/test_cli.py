import argparse

from codex_monitor.cli import cmd_run_once
from codex_monitor.config import (
    ActorFilterConfig,
    CodexMonitorConfig,
    DeliveryConfig,
    EventConfig,
    GitLabConfig,
    MonitorConfig,
)
from codex_monitor.monitors.gitlab import GitLabError


def test_run_once_catches_gitlab_error(monkeypatch, tmp_path, capsys):
    config = CodexMonitorConfig(
        monitor=MonitorConfig("test-monitor", "gitlab"),
        gitlab=GitLabConfig("gitlab.example.test", "", ("group/project",), True),
        events=EventConfig(),
        actor_filter=ActorFilterConfig(),
        delivery=DeliveryConfig(
            tmux_target="agent",
            state_path=tmp_path / "state.json",
            log_path=tmp_path / "monitor.log",
        ),
    )
    monkeypatch.setattr("codex_monitor.cli.load_config", lambda path: config)
    monkeypatch.setattr(
        "codex_monitor.cli.run_once",
        lambda config, dry_run=False: (_ for _ in ()).throw(GitLabError("name resolution failed")),
    )

    code = cmd_run_once(argparse.Namespace(config="config.yaml", dry_run=True))

    captured = capsys.readouterr()
    assert code == 2
    assert "GitLab fetch failed: name resolution failed" in captured.err
