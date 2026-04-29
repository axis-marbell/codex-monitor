import json

from codex_monitor.state import MonitorState, load_state, save_state


def test_save_state_atomic_shape(tmp_path):
    path = tmp_path / "monitor.json"
    state = MonitorState(
        last_seen_event_id_by_source={"merge_requests:group/project": "event-1"},
        pending_wake_messages=[{"event_id": "event-2", "message": "wake"}],
    )

    save_state(path, state)
    loaded = load_state(path)

    assert loaded.last_seen_event_id_by_source["merge_requests:group/project"] == "event-1"
    assert loaded.pending_wake_messages[0]["event_id"] == "event-2"
    assert json.loads(path.read_text(encoding="utf-8"))["pending_wake_messages"][0]["message"] == "wake"
