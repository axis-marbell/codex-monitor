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

By default, `tmux test` uses a conservative idle check before sending keys. If
the pane does not look idle, the test returns `queued_not_idle` and sends
nothing. For a one-off manual test, you can bypass that check:

```bash
codex-monitor tmux test \
  --target codex-agent \
  --message "Wake test from codex-monitor" \
  --no-idle-check
```

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

## Idle Check And Queued Delivery

If `delivery.idle_check` is enabled, the monitor checks the last captured tmux
pane line before sending keys. If the pane does not look idle, the wake is not
dropped. It is stored in the monitor state file and retried on later cycles.

Disable the heuristic if it is wrong for your shell or Codex setup:

```yaml
delivery:
  idle_check: false
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

## Troubleshooting

`tmux is not installed or not on PATH`
: Install tmux and retry.

`queued_not_idle`
: The target pane did not look idle. Wait for the next cycle, lower the
  strictness by setting `idle_check: false`, or use `--no-idle-check` for a
  manual test.

No wake after start
: Run `codex-monitor run-once --config <path> --dry-run`, inspect the log path,
  and confirm the GitLab token, host, project path, and tmux target.

Duplicate wakes
: Check the state file for `last_seen_event_id_by_source` and confirm every
  monitor has a unique `monitor.name`.

Self-triggered wakes
: Set `actor_filter.ignore_self_username` to the GitLab username used by the
  agent.
