"""Wake message rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from string import Formatter
from typing import Any


@dataclass(frozen=True)
class MonitorEvent:
    source: str
    event_id: str
    event_type: str
    url: str
    actor: str
    summary: str
    extras: dict[str, str] = field(default_factory=dict)


class FormatContext(dict[str, Any]):
    """Format context that supports {extras.key} placeholders."""

    def __init__(self, event: MonitorEvent) -> None:
        super().__init__(
            source=event.source,
            event_id=event.event_id,
            event_type=event.event_type,
            url=event.url,
            actor=event.actor,
            summary=truncate(event.summary),
            extras=DotMapping(event.extras),
        )

    def __missing__(self, key: str) -> str:
        return ""


class DotMapping:
    """Expose dictionary keys as format attributes."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def __getattr__(self, key: str) -> str:
        return self._values.get(key, "")


def truncate(value: str, limit: int = 80) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def render_wake_message(template: str, event: MonitorEvent) -> str:
    return Formatter().vformat(template, (), FormatContext(event))
