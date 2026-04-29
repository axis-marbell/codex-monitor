from codex_monitor.render import MonitorEvent, render_wake_message


def test_render_wake_message_truncates_summary():
    event = MonitorEvent(
        source="merge_requests",
        event_id="event-1",
        event_type="merge_request.opened",
        url="https://gitlab.example.test/group/project/-/merge_requests/1",
        actor="operator",
        summary="x" * 100,
        extras={"project": "group/project"},
    )

    message = render_wake_message("{extras.project} {event_type} {actor} {summary} {event_id} {url}", event)

    assert "group/project merge_request.opened operator" in message
    assert "event-1" in message
    assert "…" in message


def test_render_default_universal_fields():
    event = MonitorEvent(
        source="generic",
        event_id="event-1",
        event_type="object.created",
        url="https://example.test/event-1",
        actor="system",
        summary="Object created",
    )

    message = render_wake_message("{event_type} {source} {summary} {extras.missing}", event)

    assert message == "object.created generic Object created "


def test_render_monitor_specific_extras_without_renderer_changes():
    event = MonitorEvent(
        source="sentry",
        event_id="issue-123",
        event_type="error.resolved",
        url="https://sentry.example.test/issues/123",
        actor="sentry-bot",
        summary="Checkout timeout resolved",
        extras={"service": "checkout", "environment": "prod", "severity": "warning"},
    )

    message = render_wake_message(
        "{event_type} {extras.service} {extras.environment} {extras.severity} {summary}",
        event,
    )

    assert message == "error.resolved checkout prod warning Checkout timeout resolved"
