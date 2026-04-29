"""Monitor execution orchestration."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from .config import CodexMonitorConfig
from .logging_utils import append_log
from .monitors.gitlab import GitLabMonitor
from .render import MonitorEvent, render_wake_message
from .state import MonitorState, load_state, save_state
from .tmux_delivery import TmuxDelivery


def run_once(config: CodexMonitorConfig, *, dry_run: bool = False) -> int:
    """Run one monitor cycle.

    Returns the number of new wake candidates detected in this cycle.
    """
    state_path = _required_path(config.delivery.state_path)
    log_path = _required_path(config.delivery.log_path)
    state = load_state(state_path)
    effective_dry_run = dry_run or config.delivery.dry_run

    if config.insecure_literal_token:
        append_log(log_path, "warning insecure_literal_token_in_config use_env_var_reference=true")

    delivery = TmuxDelivery(config.delivery.tmux_target)
    delivered_pending = _flush_pending(config, state, delivery, log_path, effective_dry_run)

    monitor = GitLabMonitor(config.gitlab, config.events, config.actor_filter)
    try:
        events = monitor.fetch_events()
    except Exception as exc:
        state.consecutive_failures += 1
        append_log(log_path, f"fetch_failed monitor={config.monitor.name} error={type(exc).__name__}")
        save_state(state_path, state)
        raise

    state.consecutive_failures = 0
    new_events = _select_new_events(events, state)
    for event in new_events:
        message = render_wake_message(config.wake_message_template, event)
        wake = {
            "source_key": _source_key(event),
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "url": event.url,
            "actor": event.actor,
            "summary": event.summary,
            "message": message,
        }
        outcome = _deliver_or_queue(config, state, delivery, log_path, wake, effective_dry_run)
        append_log(
            log_path,
            f"event_detected source={wake['source_key']} event_id={event.event_id} "
            f"actor={event.actor} outcome={outcome}",
        )

    save_state(state_path, state)
    return len(new_events) + delivered_pending


def _required_path(path: Path | None) -> Path:
    if path is None:
        raise ValueError("path is required")
    return path


def _source_key(event: MonitorEvent) -> str:
    return f"{event.source}:{event.extras.get('project', event.source)}"


def _select_new_events(events: list[MonitorEvent], state: MonitorState) -> list[MonitorEvent]:
    grouped: dict[str, list[MonitorEvent]] = {}
    for event in events:
        grouped.setdefault(_source_key(event), []).append(event)

    selected: list[MonitorEvent] = []
    for source_key, source_events in grouped.items():
        last_seen = state.last_seen_event_id_by_source.get(source_key)
        if not source_events:
            continue
        newest = source_events[-1].event_id
        if last_seen is None:
            state.last_seen_event_id_by_source[source_key] = newest
            continue
        emit = False
        found_last = False
        for event in source_events:
            if emit:
                selected.append(event)
            if event.event_id == last_seen:
                found_last = True
                emit = True
        if not found_last:
            state.last_seen_event_id_by_source[source_key] = newest
            continue
        state.last_seen_event_id_by_source[source_key] = newest
    return selected


def _flush_pending(
    config: CodexMonitorConfig,
    state: MonitorState,
    delivery: TmuxDelivery,
    log_path: Path,
    dry_run: bool,
) -> int:
    delivered = 0
    remaining: list[dict[str, str]] = []
    for wake in state.pending_wake_messages:
        outcome = _attempt_delivery(config, state, delivery, wake, dry_run)
        append_log(
            log_path,
            f"pending_delivery event_id={wake.get('event_id', '')} "
            f"actor={wake.get('actor', '')} outcome={outcome}",
        )
        if outcome in {"delivered", "dry_run"}:
            delivered += 1
        else:
            remaining.append(wake)
    state.pending_wake_messages = remaining
    return delivered


def _deliver_or_queue(
    config: CodexMonitorConfig,
    state: MonitorState,
    delivery: TmuxDelivery,
    log_path: Path,
    wake: dict[str, str],
    dry_run: bool,
) -> str:
    outcome = _attempt_delivery(config, state, delivery, wake, dry_run)
    if outcome not in {"delivered", "dry_run"}:
        if not any(item.get("event_id") == wake.get("event_id") for item in state.pending_wake_messages):
            state.pending_wake_messages.append(wake)
    if outcome == "queued_not_idle":
        if state.idle_skip_count >= config.delivery.idle_check_max_skip:
            append_log(log_path, f"warning idle_skip_limit event_id={wake.get('event_id', '')}")
    return outcome


def _attempt_delivery(
    config: CodexMonitorConfig,
    state: MonitorState,
    delivery: TmuxDelivery,
    wake: dict[str, str],
    dry_run: bool,
) -> str:
    result = delivery.deliver(
        wake.get("message", ""),
        idle_check=config.delivery.idle_check,
        dry_run=dry_run,
    )
    if result.outcome == "queued_not_idle":
        state.idle_skip_count += 1
    elif result.success:
        state.idle_skip_count = 0
    return result.outcome


def event_to_dict(event: MonitorEvent, template: str) -> dict[str, str]:
    wake = dataclasses.asdict(event)
    wake["source_key"] = _source_key(event)
    wake["message"] = render_wake_message(template, event)
    return _stringify(wake)


def _stringify(value: dict[str, Any]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            for child_key, child_value in item.items():
                rendered[f"{key}.{child_key}"] = str(child_value)
        else:
            rendered[key] = str(item)
    return rendered
