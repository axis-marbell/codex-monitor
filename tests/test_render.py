from codex_monitor.render import MonitorEvent, render_wake_message


def test_render_wake_message_truncates_title():
    event = MonitorEvent(
        source="merge_requests",
        event_id="event-1",
        event_type="merge_request.opened",
        project="group/project",
        url="https://gitlab.example.test/group/project/-/merge_requests/1",
        actor="operator",
        title="x" * 100,
    )

    message = render_wake_message("{project} {event_type} {actor} {title} {event_id} {url}", event)

    assert "group/project merge_request.opened operator" in message
    assert "event-1" in message
    assert "…" in message
