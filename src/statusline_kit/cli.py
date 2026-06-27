from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable


CODEX_STATUS_LINE = """status_line = [
  "model-with-reasoning",
  "context-used",
  "five-hour-limit",
  "weekly-limit",
  "git-branch",
]
status_line_use_colors = true"""

CODEX_TOP_LEVEL_PREFERENCES = {
    "check_for_update_on_startup": "false",
    "project_doc_fallback_filenames": '["CLAUDE.md", "README.md"]',
    "project_doc_max_bytes": "100000",
    "tool_output_token_limit": "40000",
}

CODEX_CONFIG_SECTIONS = {
    "history": 'persistence = "save-all"\nmax_bytes = 10485760',
    "shell_environment_policy": 'inherit = "all"\nexclude = ["*TOKEN*", "*SECRET*", "*KEY*", "*PASSWORD*", "*password*"]',
    "agents": "max_threads = 6\nmax_depth = 1\njob_max_runtime_seconds = 1800",
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kt-aicoding-config",
        description="Claude Code and Codex CLI configuration kit.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("claude", help="Render one Claude Code status line from stdin JSON.")
    subparsers.add_parser("doctor", help="Show detected Claude/Codex config paths.")

    install_claude = subparsers.add_parser(
        "install-claude",
        help="Install this command as the Claude Code statusLine command.",
    )
    install_claude.add_argument("--settings", type=Path, default=default_claude_settings())
    install_claude.add_argument("--command", dest="status_command", default=default_command("claude"))

    install_codex = subparsers.add_parser(
        "install-codex",
        help="Install the recommended Codex CLI preferences and TUI status line config.",
    )
    install_codex.add_argument("--config", type=Path, default=default_codex_config())

    args = parser.parse_args(argv)

    if args.command == "claude":
        return render_claude_command()
    if args.command == "install-claude":
        backup = install_claude_statusline(args.settings, args.status_command)
        print(f"Installed Claude Code statusLine in {args.settings}")
        if backup:
            print(f"Backup: {backup}")
        return 0
    if args.command == "install-codex":
        backup = install_codex_statusline(args.config)
        print(f"Installed Codex CLI config in {args.config}")
        if backup:
            print(f"Backup: {backup}")
        return 0
    if args.command == "doctor":
        print_doctor()
        return 0

    parser.print_help()
    return 2


def default_claude_settings() -> Path:
    return Path(os.environ.get("CLAUDE_DIR", Path.home() / ".claude")) / "settings.json"


def default_codex_config() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"


def default_command(mode: str) -> str:
    script = Path(__file__).resolve().parents[2] / "bin" / "kt-statusline"
    return f"{script} {mode}"


def render_claude_command() -> int:
    raw = sys.stdin.read().strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    print(format_claude_status(payload, use_color=should_use_color()))
    return 0


def format_claude_status(payload: dict[str, Any], use_color: bool = False) -> str:
    model = first_text(
        nested(payload, "model", "display_name"),
        nested(payload, "model", "name"),
        nested(payload, "model", "id"),
        payload.get("model"),
        "Claude",
    )
    effort = first_text(
        nested(payload, "effort", "level"),
        payload.get("effort"),
        nested(payload, "model", "reasoning_effort"),
        payload.get("reasoning_effort"),
    )
    context_used = first_float(
        nested(payload, "context_window", "used_percentage"),
        nested(payload, "context_window", "used_percent"),
        nested(payload, "context", "used_percentage"),
        nested(payload, "context", "used_percent"),
        payload.get("context_used_percentage"),
    )
    five_hour_left = rate_limit_left(payload, ("five_hour", "5h"))
    weekly_left = rate_limit_left(payload, ("seven_day", "7d", "weekly"))
    cwd = first_text(
        nested(payload, "workspace", "current_dir"),
        nested(payload, "workspace", "project_dir"),
        payload.get("cwd"),
    )
    branch = git_branch(cwd)

    headline = model
    if effort:
        headline = f"{headline} {effort}"
    parts = [colorize(headline, BOLD, use_color)]
    if context_used is not None:
        parts.append(colorize(f"Context {format_percent(context_used)} used", context_color(context_used), use_color))
    if five_hour_left is not None:
        parts.append(colorize(f"5h {format_percent(five_hour_left)} left", remaining_color(five_hour_left), use_color))
    if weekly_left is not None:
        parts.append(colorize(f"weekly {format_percent(weekly_left)} left", remaining_color(weekly_left), use_color))
    if branch:
        parts.append(colorize(branch, CYAN, use_color))
    return " · ".join(parts)


def should_use_color() -> bool:
    return not os.environ.get("KT_STATUSLINE_NO_COLOR")


def colorize(text: str, color: str, enabled: bool) -> str:
    if not enabled or not color:
        return text
    return f"{color}{text}{RESET}"


def context_color(value: float) -> str:
    used = normalize_percent(value)
    if used >= 80:
        return RED
    if used >= 60:
        return YELLOW
    return GREEN


def remaining_color(value: float) -> str:
    left = normalize_percent(value)
    if left <= 20:
        return RED
    if left <= 40:
        return YELLOW
    return GREEN


def nested(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def rate_limit_left(payload: dict[str, Any], names: tuple[str, ...]) -> float | None:
    left = first_float(
        rate_limit_mapping_value(
            payload,
            names,
            ("remaining_percentage", "remaining_percent", "left_percentage", "left_percent"),
        ),
        rate_limit_value(payload, names, ("remaining_percentage", "remaining_percent", "left_percentage", "left_percent")),
    )
    if left is not None:
        return normalize_percent(left)

    used = first_float(
        rate_limit_mapping_value(payload, names, ("used_percentage", "used_percent")),
        rate_limit_value(payload, names, ("used_percentage", "used_percent")),
    )
    if used is None:
        return None
    return max(0.0, 100.0 - normalize_percent(used))


def rate_limit_mapping_value(payload: dict[str, Any], names: tuple[str, ...], keys: tuple[str, ...]) -> Any:
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return None
    for name in names:
        item = rate_limits.get(name)
        if not isinstance(item, dict):
            continue
        for key in keys:
            if key in item:
                return item[key]
    return None


def rate_limit_value(payload: dict[str, Any], names: tuple[str, ...], keys: tuple[str, ...]) -> Any:
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, list):
        return None
    normalized = {name.replace("-", "_").lower() for name in names}
    for item in rate_limits:
        if not isinstance(item, dict):
            continue
        item_name = first_text(item.get("name"), item.get("window"), item.get("type"))
        if item_name.replace("-", "_").lower() in normalized:
            for key in keys:
                if key in item:
                    return item[key]
    return None


def first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            display = value.get("display_name") or value.get("name") or value.get("id")
            if isinstance(display, str) and display.strip():
                return display.strip()
    return ""


def first_float(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (float, int)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def format_percent(value: float) -> str:
    value = normalize_percent(value)
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded}%"


def normalize_percent(value: float) -> float:
    if 0 <= value <= 1:
        return value * 100
    return value


def git_branch(cwd: str) -> str:
    if not cwd:
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    branch = result.stdout.strip()
    if result.returncode != 0 or branch == "HEAD":
        return ""
    return branch


def install_claude_statusline(settings_path: Path, command: str) -> Path | None:
    settings = read_json_object(settings_path)
    backup = backup_file(settings_path)
    settings["statusLine"] = {
        "type": "command",
        "command": command,
    }
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    return backup


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Cannot parse JSON file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected JSON object in {path}")
    return data


def install_codex_statusline(config_path: Path) -> Path | None:
    text = config_path.read_text() if config_path.exists() else ""
    backup = backup_file(config_path)
    updated = upsert_codex_config(text)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(updated)
    return backup


def upsert_codex_config(text: str) -> str:
    updated = upsert_top_level_preferences(text, CODEX_TOP_LEVEL_PREFERENCES)
    updated = upsert_tui_status_line(updated)
    for table_name, body in CODEX_CONFIG_SECTIONS.items():
        updated = upsert_table(updated, table_name, body)
    return updated


def upsert_top_level_preferences(text: str, preferences: dict[str, str]) -> str:
    lines = text.splitlines()
    first_table = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("[") and line.strip().endswith("]")),
        len(lines),
    )
    top = lines[:first_table]
    rest = lines[first_table:]
    keys = set(preferences)
    kept_top = []
    for line in top:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key in keys:
            continue
        kept_top.append(line)
    while kept_top and not kept_top[-1].strip():
        kept_top.pop()
    preference_lines = [f"{key} = {value}" for key, value in preferences.items()]
    new_top = kept_top + ([""] if kept_top else []) + preference_lines
    return "\n".join(new_top + ([""] if rest and new_top else []) + rest).rstrip() + "\n"


def upsert_tui_status_line(text: str) -> str:
    lines = text.splitlines()
    start, end = find_table(lines, "tui")
    if start is None:
        prefix = text.rstrip()
        section = "[tui]\n" + CODEX_STATUS_LINE + "\n"
        return (prefix + "\n\n" if prefix else "") + section

    section_lines = lines[start + 1 : end]
    kept = remove_tui_status_keys(section_lines)
    replacement = ["[tui]"] + CODEX_STATUS_LINE.splitlines()
    if kept:
        replacement.extend([""] + kept)
    new_lines = lines[:start] + replacement + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"


def upsert_table(text: str, table_name: str, body: str) -> str:
    lines = text.splitlines()
    start, end = find_table(lines, table_name)
    replacement = [f"[{table_name}]"] + body.splitlines()
    if start is None:
        prefix = text.rstrip()
        section = "\n".join(replacement) + "\n"
        return (prefix + "\n\n" if prefix else "") + section
    new_lines = lines[:start] + replacement + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"


def find_table(lines: list[str], table_name: str) -> tuple[int | None, int]:
    header = f"[{table_name}]"
    start = None
    for index, line in enumerate(lines):
        if line.strip() == header:
            start = index
            break
    if start is None:
        return None, len(lines)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    return start, end


def remove_tui_status_keys(lines: Iterable[str]) -> list[str]:
    kept: list[str] = []
    skipping_array = False
    for line in lines:
        stripped = line.strip()
        if skipping_array:
            if stripped.endswith("]"):
                skipping_array = False
            continue
        if stripped.startswith("status_line_use_colors"):
            continue
        if stripped.startswith("status_line"):
            if "[" in stripped and "]" not in stripped:
                skipping_array = True
            continue
        kept.append(line)
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    return kept


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    suffix = dt.datetime.now().strftime(".bak-%Y%m%d-%H%M%S")
    backup = path.with_name(path.name + suffix)
    shutil.copy2(path, backup)
    return backup


def print_doctor() -> None:
    claude = default_claude_settings()
    codex = default_codex_config()
    print(f"Claude settings: {claude} ({'exists' if claude.exists() else 'missing'})")
    print(f"Codex config:    {codex} ({'exists' if codex.exists() else 'missing'})")
    print(f"Command:         {default_command('claude')}")
