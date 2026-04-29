"""GitLab monitor backend."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from codex_monitor.config import ActorFilterConfig, EventConfig, GitLabConfig
from codex_monitor.render import MonitorEvent


class GitLabError(RuntimeError):
    """Raised when the GitLab API request fails."""


@dataclass(frozen=True)
class GitLabMonitor:
    config: GitLabConfig
    events: EventConfig
    actor_filter: ActorFilterConfig

    def fetch_events(self) -> list[MonitorEvent]:
        collected: list[MonitorEvent] = []
        for project in self.config.projects:
            if self.events.merge_requests or self.events.merge_request_comments:
                merge_requests = self._get_project_items(
                    project,
                    "merge_requests",
                    {"state": "all", "order_by": "updated_at", "sort": "asc", "per_page": "20"},
                )
                if self.events.merge_requests:
                    collected.extend(self._merge_request_events(project, merge_requests))
                if self.events.merge_request_comments:
                    collected.extend(self._note_events(project, "merge_requests", merge_requests))

            if self.events.issues or self.events.issue_comments:
                issues = self._get_project_items(
                    project,
                    "issues",
                    {"state": "all", "order_by": "updated_at", "sort": "asc", "per_page": "20"},
                )
                if self.events.issues:
                    collected.extend(self._issue_events(project, issues))
                if self.events.issue_comments:
                    collected.extend(self._note_events(project, "issues", issues))

            if self.events.pushes:
                collected.extend(self._push_events(project))
        return [event for event in collected if not self._ignored_actor(event.actor)]

    def _ignored_actor(self, actor: str) -> bool:
        return bool(self.actor_filter.ignore_self_username and actor == self.actor_filter.ignore_self_username)

    def _api_url(self, path: str, params: dict[str, str] | None = None) -> str:
        query = f"?{urlencode(params)}" if params else ""
        return f"https://{self.config.host}/api/v4/{path.lstrip('/')}{query}"

    def _request_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        headers = {"Accept": "application/json"}
        if self.config.token:
            headers["PRIVATE-TOKEN"] = self.config.token
        request = Request(self._api_url(path, params), headers=headers)
        try:
            with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is operator-configured.
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - exact urllib errors vary by Python version.
            raise GitLabError(f"GitLab API request failed for {path}: {exc}") from exc

    def _get_project_items(self, project: str, resource: str, params: dict[str, str]) -> list[dict[str, Any]]:
        encoded_project = quote(project, safe="")
        data = self._request_json(f"projects/{encoded_project}/{resource}", params)
        if not isinstance(data, list):
            raise GitLabError(f"GitLab API returned non-list response for {project}/{resource}")
        return [item for item in data if isinstance(item, dict)]

    def _merge_request_events(self, project: str, merge_requests: list[dict[str, Any]]) -> list[MonitorEvent]:
        events: list[MonitorEvent] = []
        for mr in merge_requests:
            iid = mr.get("iid", mr.get("id", "unknown"))
            state = str(mr.get("state") or "unknown")
            actor = _username(mr.get("author"))
            events.append(
                MonitorEvent(
                    source="merge_requests",
                    event_id=f"{project}:mr:{iid}:{state}:{mr.get('updated_at', '')}",
                    event_type=f"merge_request.{state}",
                    project=project,
                    url=str(mr.get("web_url") or ""),
                    actor=actor,
                    title=str(mr.get("title") or f"MR !{iid}"),
                )
            )
        return events

    def _issue_events(self, project: str, issues: list[dict[str, Any]]) -> list[MonitorEvent]:
        events: list[MonitorEvent] = []
        for issue in issues:
            iid = issue.get("iid", issue.get("id", "unknown"))
            state = str(issue.get("state") or "unknown")
            actor = _username(issue.get("author"))
            events.append(
                MonitorEvent(
                    source="issues",
                    event_id=f"{project}:issue:{iid}:{state}:{issue.get('updated_at', '')}",
                    event_type=f"issue.{state}",
                    project=project,
                    url=str(issue.get("web_url") or ""),
                    actor=actor,
                    title=str(issue.get("title") or f"Issue #{iid}"),
                )
            )
        return events

    def _note_events(self, project: str, resource: str, items: list[dict[str, Any]]) -> list[MonitorEvent]:
        source = "notes"
        events: list[MonitorEvent] = []
        for item in items[:10]:
            iid = item.get("iid")
            if iid is None:
                continue
            notes = self._get_project_items(
                project,
                f"{resource}/{iid}/notes",
                {"order_by": "updated_at", "sort": "asc", "per_page": "20"},
            )
            for note in notes:
                if note.get("system"):
                    continue
                note_id = note.get("id", "unknown")
                actor = _username(note.get("author"))
                event_type = "merge_request.comment" if resource == "merge_requests" else "issue.comment"
                title = str(item.get("title") or event_type)
                events.append(
                    MonitorEvent(
                        source=source,
                        event_id=f"{project}:{resource}:{iid}:note:{note_id}",
                        event_type=event_type,
                        project=project,
                        url=str(note.get("web_url") or item.get("web_url") or ""),
                        actor=actor,
                        title=title,
                    )
                )
        return events

    def _push_events(self, project: str) -> list[MonitorEvent]:
        encoded_project = quote(project, safe="")
        data = self._request_json(
            f"projects/{encoded_project}/events",
            {"action": "pushed", "sort": "asc", "per_page": "20"},
        )
        if not isinstance(data, list):
            raise GitLabError(f"GitLab API returned non-list response for {project}/events")
        events: list[MonitorEvent] = []
        for event in data:
            if not isinstance(event, dict):
                continue
            event_id = event.get("id", "unknown")
            actor = str(event.get("author_username") or _username(event.get("author")) or "unknown")
            target_title = str(event.get("target_title") or "push event")
            events.append(
                MonitorEvent(
                    source="pushes",
                    event_id=f"{project}:push:{event_id}",
                    event_type="push",
                    project=project,
                    url=str(event.get("target_url") or ""),
                    actor=actor,
                    title=target_title,
                )
            )
        return events


def _username(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("username") or value.get("name") or "unknown")
    return "unknown"
