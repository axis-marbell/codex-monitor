from pathlib import Path

from codex_monitor.config import load_config


def test_load_config_expands_env_and_defaults_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_MONITOR_GITLAB_HOST", "gitlab.example.test")
    monkeypatch.setenv("CODEX_MONITOR_GITLAB_TOKEN", "fake-token")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    config_path = tmp_path / "monitor.yaml"
    config_path.write_text(
        """
monitor:
  name: test-monitor
  type: gitlab
gitlab:
  host: ${CODEX_MONITOR_GITLAB_HOST}
  token: ${CODEX_MONITOR_GITLAB_TOKEN}
  projects:
    - group/project
delivery:
  tmux_target: agent:0.0
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.gitlab.host == "gitlab.example.test"
    assert config.gitlab.token == "fake-token"
    assert config.gitlab.token_from_env is True
    assert config.insecure_literal_token is False
    assert config.delivery.state_path == tmp_path / "state" / "codex-monitor" / "test-monitor.json"


def test_literal_token_is_warnable(tmp_path):
    config_path = Path(tmp_path) / "monitor.yaml"
    config_path.write_text(
        """
monitor:
  name: test-monitor
  type: gitlab
gitlab:
  host: gitlab.com
  token: fake-literal-token
  projects:
    - group/project
delivery:
  tmux_target: agent
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.insecure_literal_token is True
    assert config.gitlab.token == "fake-literal-token"
