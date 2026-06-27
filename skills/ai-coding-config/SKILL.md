---
name: ai-coding-config
description: Configure Claude Code and Codex CLI preferences for KT AI Coding. Use when the user asks to add, install, update, or standardize Claude Code/Codex config, status bars/status lines, safe Codex defaults, history/shell/agent preferences, or reusable AI coding configuration.
---

# AI Coding Config

## Workflow

Configure both tools with the upstream installer:

```bash
python3 -c "$(curl -fsSL https://raw.githubusercontent.com/kt-aicoding/cc-codex-config/main/scripts/install.py)"
```

This installs:

- Claude Code `statusLine` command at `~/.kt-aicoding/cc-codex-config/kt-statusline`
- Codex CLI safe preferences and `[tui].status_line` in `~/.codex/config.toml`

The target display is:

```text
<model> <effort> · Context <n>% used · 5h <n>% left · weekly <n>% left · <git-branch>
```

Claude Code uses ANSI color warnings: context used turns yellow at 60% and red at 80%; 5h/weekly remaining turns yellow at 40% and red at 20%. Set `KT_STATUSLINE_NO_COLOR=1` to disable color.

After installation, tell the user to restart Claude Code and Codex so both tools reload their config.

## Local Development

When working inside this repository, prefer the local installer while testing changes:

```bash
python3 scripts/install.py
```

Run `python3 -m unittest` before committing changes.
