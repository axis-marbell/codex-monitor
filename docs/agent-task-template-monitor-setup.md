# Agent Task Template: Monitor Setup

Use this template when an operator asks you to set up a `codex-monitor`
monitor. Fill it in, then save the completed version in your own memory store.

## Operator Hand-Off

- Monitor type:
- Source host URL:
- Source projects/resources:
- Token location: env var or local secrets manager, never chat text
- Tmux target:
- Wake message requirement:

Stop if any required item is missing.

## Tmux Target Discovery

Run:

```bash
codex-monitor tmux detect
```

If not inside tmux, create or ask the operator to create a named session:

```bash
tmux new -s <agent-name>
```

Resolved target:

```text
<target>
```

## Self-Test

Run:

```bash
codex-monitor tmux test --target <target> --message "Wake test from codex-monitor"
```

This sends without an idle check. That is the expected setup for active Codex
panes.

Do not enable the experimental idle check during normal setup. It can
misclassify an active Codex pane as not idle and queue valid wake messages
instead of delivering them.

Only if the operator explicitly wants to test the heuristic, run:

```bash
codex-monitor tmux test --target <target> --message "Wake test from codex-monitor" --idle-check
```

Result:

```text
<result>
```

## Config Write

Write the monitor YAML to:

```text
~/.config/codex-monitor/<name>.yaml
```

Set file mode:

```bash
chmod 600 ~/.config/codex-monitor/<name>.yaml
```

Use env-var references for secrets. Do not write literal tokens into the file
unless the operator explicitly accepts that local risk.

Set delivery with the idle check disabled unless the operator has already
validated the experimental prompt heuristic:

```yaml
delivery:
  tmux_target: <target>
  idle_check: false
```

Configure the wake message with universal fields first:

```text
{source}
{event_type}
{url}
{actor}
{summary}
{event_id}
```

Use monitor-specific `extras` only when the operator needs source-specific
context. For GitLab, `{extras.project}` names the configured project path.
Other GitLab extras may include `{extras.mr_iid}`, `{extras.issue_iid}`,
`{extras.note_id}`, and `{extras.state}` depending on the event.

Example GitLab-specific wake template:

```yaml
wake_message_template: |
  [wake-codex] {extras.project}: {event_type}
  URL:    {url}
  Actor:  {actor}
  Summary: {summary}
  ID:     {event_id}

  Action: source the latest state from the URL before acting.
```

For a new monitor type, keep the same universal fields and add source-specific
operator context under `extras`. For example, a future Sentry monitor could
render `{extras.service}`, `{extras.environment}`, and `{extras.severity}`
without changing the renderer. See `examples/sentry-monitor.yaml` for the
stubbed envelope shape.

## Dry-Run Verification

Run:

```bash
codex-monitor run-once --config ~/.config/codex-monitor/<name>.yaml --dry-run
```

Record:

- Authentication succeeded:
- Events parsed:
- Would-wake output looked correct:
- State/log paths:

## Background Start

Run:

```bash
codex-monitor start --config ~/.config/codex-monitor/<name>.yaml
codex-monitor status --config ~/.config/codex-monitor/<name>.yaml
```

Record PID/status:

```text
<status>
```

## Save The Workflow

Save this filled template in your memory store with:

- monitor type
- config path
- tmux target
- state path
- log path
- verification result
- operator constraints

Next time, start from the saved instance, not the blank template.
