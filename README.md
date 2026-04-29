# codex-monitor

`codex-monitor` runs small monitor scripts that wake a Codex agent by sending
a short message into the agent's tmux pane. The first supported source is
GitLab.

The wake transport is intentionally simple:

1. A monitor detects an event.
2. It renders a configured wake message.
3. It delivers that message with `tmux send-keys`.

No GitLab token should be pasted into an agent chat. The operator writes a
local YAML file that references environment variables, and the monitor reads
that file.

## Install For Local Development

```bash
git clone https://github.com/axis-marbell/codex-monitor.git
cd codex-monitor
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## Tmux Setup

Check whether `tmux` exists:

```bash
tmux -V
```

If the agent is already running inside tmux, detect the current target:

```bash
codex-monitor tmux detect
```

That prints a target like:

```text
agent:0.0
```

If the agent is not inside tmux, create a named session first:

```bash
tmux new -s codex-agent
```

In another terminal, list sessions:

```bash
tmux list-sessions
```

Then test delivery:

```bash
codex-monitor tmux test \
  --target codex-agent \
  --message "Wake test from codex-monitor"
```

By default, `tmux test` sends without an idle check. This is the recommended
mode for active Codex panes.

An experimental idle check can be enabled explicitly:

```bash
codex-monitor tmux test \
  --target codex-agent \
  --message "Wake test from codex-monitor" \
  --idle-check
```

The idle check uses a conservative prompt heuristic. If the pane does not look
idle, the test returns `queued_not_idle` and sends nothing. Active Codex panes
can be misclassified as not idle, so do not enable this unless you have verified
it against your exact tmux setup.

## Why Two `send-keys` Calls

Delivery uses two tmux calls with a one-second gap:

```bash
tmux send-keys -t "$TARGET" "$WAKE_MESSAGE"
sleep 1
tmux send-keys -t "$TARGET" Enter
```

Do not combine message text and Enter into one command. Existing team usage has
seen the Enter key dropped or treated as text when sent as part of a combined
call.

## GitLab Setup

The operator creates a GitLab personal access token in the GitLab UI. For v1,
`read_api` is enough. Export it in the shell that starts the monitor:

```bash
export CODEX_MONITOR_GITLAB_TOKEN='<token>'
export CODEX_MONITOR_GITLAB_HOST='gitlab.com'
```

Copy the example config:

```bash
mkdir -p ~/.config/codex-monitor
cp examples/gitlab-monitor.yaml ~/.config/codex-monitor/gitlab-monitor.yaml
chmod 600 ~/.config/codex-monitor/gitlab-monitor.yaml
```

Edit the copied file and fill in:

- GitLab host
- project paths
- tmux target
- self username to suppress self-triggered wakes

The example references `${CODEX_MONITOR_GITLAB_TOKEN}`. Do not replace that
with a literal token unless this is a throwaway local test; if a literal token
is found, the monitor logs a startup warning.

Run one cycle without sending tmux keys:

```bash
codex-monitor run-once \
  --config ~/.config/codex-monitor/gitlab-monitor.yaml \
  --dry-run
```

Start the monitor in the background:

```bash
codex-monitor start --config ~/.config/codex-monitor/gitlab-monitor.yaml
codex-monitor status --config ~/.config/codex-monitor/gitlab-monitor.yaml
```

Stop it:

```bash
codex-monitor stop --config ~/.config/codex-monitor/gitlab-monitor.yaml
```

## Experimental Idle Check

`delivery.idle_check` defaults to `false`. Leave it disabled for Codex agents
unless you have verified the prompt heuristic against the exact tmux pane the
monitor will wake.

If enabled, the monitor checks the last captured tmux pane line before sending
keys. If the pane does not look idle, the wake is not dropped. It is stored in
the monitor state file and retried on later cycles. In live testing, active
Codex panes were misclassified as not idle and valid wakes stayed queued until
the check was disabled.

Opt in only for a known-compatible shell prompt:

```yaml
delivery:
  idle_check: true
```

## State And Logs

Default paths:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/codex-monitor/<monitor-name>.json
${XDG_STATE_HOME:-$HOME/.local/state}/codex-monitor/<monitor-name>.log
```

State is written atomically with temp-file plus rename. Logs record decisions
and outcomes, but do not write tokens or full wake message bodies.

The first run with a new state file arms the monitor and records the latest
seen event IDs without replaying existing history. Future cycles wake only for
newer events.

## GitLab V1 Events

Supported in the MVP:

- merge request updates
- merge request comments
- issue updates
- issue comments
- pushes

Deferred from v1:

- pipeline failures
- approvals
- scheduled jobs

## Wake Message Templates

The default wake template uses only universal event fields:

```text
[wake-codex] {event_type} ({source})
URL:    {url}
Actor:  {actor}
Summary: {summary}
ID:     {event_id}

Action: source the latest state from the URL before acting.
```

Universal fields are available for every monitor type:

- `{source}`: monitor source stream, such as `merge_requests`, `issues`, or `pushes`
- `{event_type}`: normalized event name, such as `merge_request.opened`
- `{url}`: source URL to inspect before acting
- `{actor}`: username or actor that triggered the event
- `{summary}`: short event descriptor
- `{event_id}`: stable dedupe ID

Monitor-specific fields live under `extras`. GitLab events include
`{extras.project}` and may also include keys such as `{extras.mr_iid}`,
`{extras.issue_iid}`, `{extras.note_id}`, or `{extras.state}` depending on the
event type.

GitLab-flavored custom template:

```yaml
wake_message_template: |
  [wake-codex] {extras.project}: {event_type}
  URL:    {url}
  Actor:  {actor}
  Title:  {summary}
  ID:     {event_id}

  Action: source the latest state from the URL before acting.
```

If an `extras` key is missing, it renders as an empty string. Prefer universal
fields in reusable templates and use `extras` only for monitor-specific
operator-facing messages.

See `examples/sentry-monitor.yaml` for a non-runnable second-monitor envelope
example. It shows how a future monitor can add keys such as
`{extras.service}`, `{extras.environment}`, and `{extras.severity}` without
changing the renderer.

## Troubleshooting

`tmux is not installed or not on PATH`
: Install tmux and retry.

`queued_not_idle`
: The experimental idle check is enabled and the target pane did not look idle.
  Active Codex panes can trigger this incorrectly. Set `idle_check: false` and
  rerun one monitor cycle to flush queued wake messages.

No wake after start
: Run `codex-monitor run-once --config <path> --dry-run`, inspect the log path,
  and confirm the GitLab token, host, project path, and tmux target.

Duplicate wakes
: Check the state file for `last_seen_event_id_by_source` and confirm every
  monitor has a unique `monitor.name`.

Self-triggered wakes
: Set `actor_filter.ignore_self_username` to the GitLab username used by the
  agent.

## Contributing

See `CONTRIBUTING.md` for contributor policy, local validation, monitor safety,
and documentation expectations.

## License

MIT. See `LICENSE`.
