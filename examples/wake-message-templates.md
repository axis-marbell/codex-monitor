# Wake Message Templates

Default:

```text
[wake-codex] {event_type} ({source})
URL:    {url}
Actor:  {actor}
Summary: {summary}
ID:     {event_id}

Action: source the latest state from the URL before acting.
```

Universal fields:

- `{source}`
- `{event_type}`
- `{url}`
- `{actor}`
- `{summary}`
- `{event_id}`

Monitor-specific fields live under `extras`.

Known GitLab extras:

- `{extras.project}`: configured GitLab project path
- `{extras.mr_iid}`: merge request IID, for merge request events
- `{extras.issue_iid}`: issue IID, for issue events
- `{extras.note_id}`: note/comment ID, for comment events
- `{extras.state}`: GitLab state, for merge request or issue state events

GitLab example:

```text
[wake-codex] {extras.project}: {event_type}
URL:    {url}
Actor:  {actor}
Title:  {summary}
ID:     {event_id}
```

Future monitor example:

```text
[wake-codex] {event_type} ({extras.service})
URL:    {url}
Actor:  {actor}
Summary: {summary}
Env:    {extras.environment}
Level:  {extras.severity}
ID:     {event_id}
```

That Sentry-shaped example is only a template contract until a Sentry backend is
implemented. The important point is that a new monitor supplies universal fields
plus its own `extras` keys; the renderer does not need a source-specific field.

Keep wake messages short. They are pointers, not snapshots. The receiving
agent should always source the latest state from the URL before acting.
