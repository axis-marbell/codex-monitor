from codex_monitor.config import ActorFilterConfig, EventConfig, GitLabConfig
from codex_monitor.monitors.gitlab import GitLabMonitor


class FakeGitLabMonitor(GitLabMonitor):
    def _request_json(self, path, params=None):
        if path.endswith("/merge_requests"):
            return [
                {
                    "iid": 1,
                    "state": "opened",
                    "updated_at": "2026-04-29T00:00:00Z",
                    "web_url": "https://gitlab.example.test/group/project/-/merge_requests/1",
                    "title": "Add monitor",
                    "author": {"username": "operator"},
                }
            ]
        if path.endswith("/merge_requests/1/notes"):
            return [
                {
                    "id": 10,
                    "system": False,
                    "web_url": "https://gitlab.example.test/group/project/-/merge_requests/1#note_10",
                    "author": {"username": "reviewer"},
                },
                {
                    "id": 11,
                    "system": False,
                    "web_url": "https://gitlab.example.test/group/project/-/merge_requests/1#note_11",
                    "author": {"username": "agent-user"},
                },
            ]
        if path.endswith("/issues"):
            return []
        return []


def test_gitlab_monitor_builds_events_and_filters_self():
    monitor = FakeGitLabMonitor(
        GitLabConfig("gitlab.example.test", "token", ("group/project",), True),
        EventConfig(merge_requests=True, merge_request_comments=True, issues=False, issue_comments=False),
        ActorFilterConfig(ignore_self_username="agent-user"),
    )

    events = monitor.fetch_events()

    assert [event.event_type for event in events] == ["merge_request.opened", "merge_request.comment"]
    assert events[1].actor == "reviewer"
    assert events[0].summary == "Add monitor"
    assert events[0].extras["project"] == "group/project"
    assert events[0].extras["mr_iid"] == "1"
