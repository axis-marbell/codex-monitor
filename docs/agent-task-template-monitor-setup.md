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

If the pane does not look idle, either wait and retry or use a deliberate
manual test:

```bash
codex-monitor tmux test --target <target> --message "Wake test from codex-monitor" --no-idle-check
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
