"""Configuration loading for codex-monitor."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a monitor config is invalid."""


_ENV_REF_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_ENV_EXPAND_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
DEFAULT_WAKE_MESSAGE_TEMPLATE = (
    "[wake-codex] {event_type} ({source})\n"
    "URL:    {url}\n"
    "Actor:  {actor}\n"
    "Summary: {summary}\n"
    "ID:     {event_id}\n\n"
    "Action: source the latest state from the URL before acting."
)


@dataclass(frozen=True)
class MonitorConfig:
    name: str
    type: str


@dataclass(frozen=True)
class GitLabConfig:
    host: str
    token: str
    projects: tuple[str, ...]
    token_from_env: bool


@dataclass(frozen=True)
class EventConfig:
    merge_requests: bool = True
    merge_request_comments: bool = True
    issues: bool = True
    issue_comments: bool = True
    pushes: bool = False
    pipelines: bool = False


@dataclass(frozen=True)
class ActorFilterConfig:
    ignore_self_username: str = ""


@dataclass(frozen=True)
class DeliveryConfig:
    tmux_target: str
    poll_interval_seconds: int = 90
    idle_check: bool = False
    idle_check_max_skip: int = 5
    dry_run: bool = False
    state_path: Path | None = None
    log_path: Path | None = None


@dataclass(frozen=True)
class CodexMonitorConfig:
    monitor: MonitorConfig
    gitlab: GitLabConfig
    events: EventConfig = field(default_factory=EventConfig)
    actor_filter: ActorFilterConfig = field(default_factory=ActorFilterConfig)
    delivery: DeliveryConfig = field(default_factory=lambda: DeliveryConfig(""))
    wake_message_template: str = DEFAULT_WAKE_MESSAGE_TEMPLATE
    insecure_literal_token: bool = False


def default_state_dir() -> Path:
    """Return the XDG state directory for codex-monitor."""
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base).expanduser() / "codex-monitor"
    return Path.home() / ".local" / "state" / "codex-monitor"


def expand_env_refs(value: Any) -> Any:
    """Expand ${ENV_VAR} placeholders inside config values."""
    if isinstance(value, dict):
        return {key: expand_env_refs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env_refs(item) for item in value]
    if isinstance(value, str):
        return _ENV_EXPAND_RE.sub(lambda match: os.environ.get(match.group(1), ""), value)
    return value


def _is_env_ref(value: Any) -> bool:
    return isinstance(value, str) and _ENV_REF_RE.match(value) is not None


def _mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value


def _bool(mapping: dict[str, Any], key: str, default: bool) -> bool:
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{key} must be true or false")


def _int(mapping: dict[str, Any], key: str, default: int) -> int:
    value = mapping.get(key, default)
    if isinstance(value, int):
        return value
    raise ConfigError(f"{key} must be an integer")


def load_config(path: str | Path) -> CodexMonitorConfig:
    """Load a codex-monitor YAML config."""
    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as handle:
        raw_loaded = yaml.safe_load(handle) or {}
    if not isinstance(raw_loaded, dict):
        raise ConfigError("config root must be a mapping")

    raw_gitlab = _mapping(raw_loaded, "gitlab")
    raw_token = raw_gitlab.get("token", "")
    token_from_env = _is_env_ref(raw_token)
    insecure_literal_token = bool(raw_token) and not token_from_env

    expanded = expand_env_refs(raw_loaded)

    monitor_raw = _mapping(expanded, "monitor")
    monitor = MonitorConfig(
        name=str(monitor_raw.get("name") or "").strip(),
        type=str(monitor_raw.get("type") or "").strip(),
    )
    if not monitor.name:
        raise ConfigError("monitor.name is required")
    if monitor.type != "gitlab":
        raise ConfigError("only monitor.type=gitlab is supported in v1")

    gitlab_raw = _mapping(expanded, "gitlab")
    host = str(gitlab_raw.get("host") or os.environ.get("CODEX_MONITOR_GITLAB_HOST") or "gitlab.com").strip()
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")
    token = str(gitlab_raw.get("token") or "").strip()
    projects_raw = gitlab_raw.get("projects", [])
    if not isinstance(projects_raw, list) or not projects_raw:
        raise ConfigError("gitlab.projects must contain at least one project path")
    projects = tuple(str(project).strip().strip("/") for project in projects_raw if str(project).strip())
    if not projects:
        raise ConfigError("gitlab.projects must contain at least one project path")

    events_raw = _mapping(expanded, "events")
    events = EventConfig(
        merge_requests=_bool(events_raw, "merge_requests", True),
        merge_request_comments=_bool(events_raw, "merge_request_comments", True),
        issues=_bool(events_raw, "issues", True),
        issue_comments=_bool(events_raw, "issue_comments", True),
        pushes=_bool(events_raw, "pushes", False),
        pipelines=_bool(events_raw, "pipelines", False),
    )

    actor_raw = _mapping(expanded, "actor_filter")
    actor_filter = ActorFilterConfig(
        ignore_self_username=str(actor_raw.get("ignore_self_username") or "").strip(),
    )

    delivery_raw = _mapping(expanded, "delivery")
    state_dir = default_state_dir()
    state_path_raw = delivery_raw.get("state_path")
    log_path_raw = delivery_raw.get("log_path")
    delivery = DeliveryConfig(
        tmux_target=str(delivery_raw.get("tmux_target") or "").strip(),
        poll_interval_seconds=_int(delivery_raw, "poll_interval_seconds", 90),
        idle_check=_bool(delivery_raw, "idle_check", False),
        idle_check_max_skip=_int(delivery_raw, "idle_check_max_skip", 5),
        dry_run=_bool(delivery_raw, "dry_run", False),
        state_path=Path(str(state_path_raw)).expanduser() if state_path_raw else state_dir / f"{monitor.name}.json",
        log_path=Path(str(log_path_raw)).expanduser() if log_path_raw else state_dir / f"{monitor.name}.log",
    )

    template = str(expanded.get("wake_message_template") or DEFAULT_WAKE_MESSAGE_TEMPLATE)

    return CodexMonitorConfig(
        monitor=monitor,
        gitlab=GitLabConfig(host=host, token=token, projects=projects, token_from_env=token_from_env),
        events=events,
        actor_filter=actor_filter,
        delivery=delivery,
        wake_message_template=template,
        insecure_literal_token=insecure_literal_token,
    )
