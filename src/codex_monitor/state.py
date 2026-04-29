"""Persistent monitor state with atomic writes."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 form."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MonitorState:
    last_seen_event_id_by_source: dict[str, str] = field(default_factory=dict)
    monitor_armed_at: str = field(default_factory=utc_now)
    consecutive_failures: int = 0
    idle_skip_count: int = 0
    pending_wake_messages: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MonitorState":
        pending_raw = raw.get("pending_wake_messages", [])
        pending = pending_raw if isinstance(pending_raw, list) else []
        last_seen_raw = raw.get("last_seen_event_id_by_source", {})
        last_seen = last_seen_raw if isinstance(last_seen_raw, dict) else {}
        return cls(
            last_seen_event_id_by_source={
                str(key): str(value) for key, value in last_seen.items()
            },
            monitor_armed_at=str(raw.get("monitor_armed_at") or utc_now()),
            consecutive_failures=int(raw.get("consecutive_failures") or 0),
            idle_skip_count=int(raw.get("idle_skip_count") or 0),
            pending_wake_messages=[
                {str(key): str(value) for key, value in item.items()}
                for item in pending
                if isinstance(item, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_seen_event_id_by_source": self.last_seen_event_id_by_source,
            "monitor_armed_at": self.monitor_armed_at,
            "consecutive_failures": self.consecutive_failures,
            "idle_skip_count": self.idle_skip_count,
            "pending_wake_messages": self.pending_wake_messages,
        }


def load_state(path: Path) -> MonitorState:
    """Load state from disk, returning a fresh state if absent."""
    if not path.exists():
        return MonitorState()
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        return MonitorState()
    return MonitorState.from_dict(raw)


def save_state(path: Path, state: MonitorState) -> None:
    """Atomically save state using temp file plus rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, path)
