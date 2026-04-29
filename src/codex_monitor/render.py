"""Wake message rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonitorEvent:
    source: str
    event_id: str
    event_type: str
    project: str
    url: str
    actor: str
    title: str


def truncate(value: str, limit: int = 80) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def render_wake_message(template: str, event: MonitorEvent) -> str:
    return template.format(
        project=event.project,
        event_type=event.event_type,
        url=event.url,
        actor=event.actor,
        title=truncate(event.title),
        event_id=event.event_id,
    )
