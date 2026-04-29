# Wake Message Templates

Default:

```text
[wake-codex] {project}: {event_type}
URL:    {url}
Actor:  {actor}
Title:  {title}
ID:     {event_id}

Action: source the latest state from the URL before acting.
```

Available fields:

- `{project}`
- `{event_type}`
- `{url}`
- `{actor}`
- `{title}`
- `{event_id}`

Keep wake messages short. They are pointers, not snapshots. The receiving
agent should always source the latest state from the URL before acting.
