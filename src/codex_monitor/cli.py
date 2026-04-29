"""Command-line interface for codex-monitor."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .config import ConfigError, load_config
from .monitors.gitlab import GitLabError
from .runner import run_once
from .tmux_delivery import TmuxDelivery, detect_current_target, tmux_available


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-monitor")
    subparsers = parser.add_subparsers(required=True)

    tmux_parser = subparsers.add_parser("tmux", help="Inspect or test tmux delivery")
    tmux_sub = tmux_parser.add_subparsers(required=True)
    detect_parser = tmux_sub.add_parser("detect", help="Print the current tmux target")
    detect_parser.set_defaults(func=cmd_tmux_detect)
    test_parser = tmux_sub.add_parser("test", help="Send a test wake message to a tmux target")
    test_parser.add_argument("--target", required=True)
    test_parser.add_argument("--message", default="Wake test from codex-monitor")
    test_parser.add_argument(
        "--idle-check",
        action="store_true",
        help="Experimental: queue instead of sending if the target pane does not look idle",
    )
    test_parser.add_argument(
        "--no-idle-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    test_parser.set_defaults(func=cmd_tmux_test)

    run_parser = subparsers.add_parser("run-once", help="Run one monitor cycle")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.set_defaults(func=cmd_run_once)

    start_parser = subparsers.add_parser("start", help="Start a background monitor")
    start_parser.add_argument("--config", required=True)
    start_parser.set_defaults(func=cmd_start)

    stop_parser = subparsers.add_parser("stop", help="Stop a background monitor")
    stop_parser.add_argument("--config", required=True)
    stop_parser.set_defaults(func=cmd_stop)

    status_parser = subparsers.add_parser("status", help="Show background monitor status")
    status_parser.add_argument("--config", required=True)
    status_parser.set_defaults(func=cmd_status)

    loop_parser = subparsers.add_parser("_loop", help=argparse.SUPPRESS)
    loop_parser.add_argument("--config", required=True)
    loop_parser.set_defaults(func=cmd_loop)
    return parser


def cmd_tmux_detect(_args: argparse.Namespace) -> int:
    target = detect_current_target()
    if target:
        print(target)
        return 0
    if not tmux_available():
        print("tmux is not installed or not on PATH", file=sys.stderr)
    else:
        print("not running inside a tmux pane", file=sys.stderr)
    return 1


def cmd_tmux_test(args: argparse.Namespace) -> int:
    result = TmuxDelivery(args.target).deliver(
        args.message,
        idle_check=args.idle_check and not args.no_idle_check,
    )
    print(result.outcome)
    if result.reason:
        print(result.reason, file=sys.stderr)
    return 0 if result.success else 1


def cmd_run_once(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        count = run_once(config, dry_run=args.dry_run)
    except GitLabError as exc:
        print(f"GitLab fetch failed: {exc}", file=sys.stderr)
        return 2
    print(f"processed {count} wake candidate(s)")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    pid_path = _pid_path(config)
    if _read_live_pid(pid_path):
        print(f"codex-monitor already running (PID {_read_live_pid(pid_path)})")
        return 0
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = config.delivery.log_path
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "codex_monitor.cli", "_loop", "--config", str(Path(args.config).expanduser())]
    with open(os.devnull, "wb") as devnull:
        process = subprocess.Popen(
            command,
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
        )
    pid_path.write_text(str(process.pid), encoding="utf-8")
    print(f"started codex-monitor PID {process.pid}")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    pid_path = _pid_path(config)
    pid = _read_live_pid(pid_path)
    if not pid:
        print("codex-monitor is not running")
        return 0
    os.kill(pid, signal.SIGTERM)
    pid_path.unlink(missing_ok=True)
    print(f"stopped codex-monitor PID {pid}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    pid = _read_live_pid(_pid_path(config))
    if pid:
        print(f"codex-monitor is running (PID {pid})")
        return 0
    print("codex-monitor is not running")
    return 1


def cmd_loop(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    while True:
        try:
            run_once(config)
        except Exception:
            pass
        time.sleep(config.delivery.poll_interval_seconds)


def _pid_path(config) -> Path:
    state_path = config.delivery.state_path
    if state_path is None:
        raise ValueError("state path is required")
    return state_path.with_suffix(".pid")


def _read_live_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


if __name__ == "__main__":
    raise SystemExit(main())
