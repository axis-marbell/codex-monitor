# Contributing

`codex-monitor` is a small monitor harness for waking Codex agents through
tmux. Contributions should keep that surface simple, auditable, and safe to run
on private infrastructure.

## Ground Rules

- Keep monitors read-only unless an issue explicitly asks for write behavior.
- Do not commit tokens, private hostnames beyond documented examples, local
  state files, logs, PID files, or generated caches.
- Use environment-variable references for credentials in examples.
- Keep wake messages short. They should point the receiving agent at source
  state, not snapshot private data into tmux.
- Preserve the two-call tmux delivery pattern: send message text, wait briefly,
  then send `Enter`.
- Treat `delivery.idle_check` as experimental. Leave it disabled in examples
  and setup docs unless the exact tmux prompt heuristic has been validated.

## Development Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Branch And PR Workflow

1. Branch from current `main`.
2. Keep each PR focused on one behavior or documentation change.
3. Link the issue the PR resolves when one exists.
4. Include validation in the PR body.
5. Do not include unrelated formatting churn.

Only `axis-marbell` and `mlops-kelvin` may merge PRs to `main`. Other
contributors should open PRs and wait for one of those maintainers to merge.

Required local checks before opening a PR:

```bash
. .venv/bin/activate
pytest
git diff --check
```

## Monitor Changes

When adding or changing a monitor source:

- Use the universal `MonitorEvent` fields: `source`, `event_id`,
  `event_type`, `url`, `actor`, and `summary`.
- Put source-specific values under `extras`.
- Do not change `render.py` for a new monitor type unless the universal
  envelope is insufficient and the issue explains why.
- Add examples that show the operator-facing config shape.
- Add deterministic tests with fake API responses.

## Documentation

Documentation is part of the product. New agents should be able to install,
configure, test, and operate a monitor from the README and examples without
reading implementation files.

Update docs when a change affects:

- config keys or defaults
- tmux delivery behavior
- state or log behavior
- token scope requirements
- monitor event fields
- operator troubleshooting

## Security And Privacy

Never paste real tokens into issues, PRs, docs, tests, or chat transcripts. If
a bug requires showing a request, redact credentials and private payloads while
preserving the endpoint, status code, and error text needed for diagnosis.

If a change could increase wake volume or expose private project data in a wake
message, call that out in the PR body.

## License

By contributing, you agree that your contribution is provided under the MIT
license in this repository.
