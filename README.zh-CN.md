# cc-codex-config

我的 Claude Code（cc）和 Codex CLI 配置仓库，面向 Warp 终端使用场景维护。

这里统一保存可公开的 AI Coding 配置：状态栏、Codex 偏好、Warp 注意事项、操作资料、Codex Skill、profile 模板和一键安装脚本。状态栏只是第一个模块，后续 cc / Codex 相关的安全配置和个人偏好都放在这里维护。

## 一句话配置

```bash
python3 -c "$(curl -fsSL https://raw.githubusercontent.com/kt-aicoding/cc-codex-config/main/scripts/install.py)"
```

运行后重启 Claude Code 和 Codex。

安装脚本会先备份原配置，再增量写入安全配置：

- Claude Code：`~/.claude/settings.json`
- Codex CLI：`~/.codex/config.toml`
- 本地状态栏命令：`~/.kt-aicoding/cc-codex-config/kt-statusline`

## 快速入口

| 内容 | 路径 |
| --- | --- |
| 一键安装脚本 | [scripts/install.py](scripts/install.py) |
| Codex 配置片段 | [configs/codex/config.toml](configs/codex/config.toml) |
| Claude Code 状态栏配置片段 | [configs/claude/settings.statusline.json](configs/claude/settings.statusline.json) |
| Warp 使用建议 | [configs/warp/README.md](configs/warp/README.md) |
| Codex profile 模板 | [configs/codex/profiles/](configs/codex/profiles/) |
| 操作资料 | [docs/operations/](docs/operations/) |
| 相关项目与取舍 | [docs/related-projects.md](docs/related-projects.md) |
| Codex Skill | [skills/ai-coding-config/SKILL.md](skills/ai-coding-config/SKILL.md) |

## 会配置什么

### Warp

- 检测 `TERM_PROGRAM=WarpTerminal` 或 `WARP_*` 环境变量。
- Claude Code 状态栏颜色不会被 Warp 默认导出的 `NO_COLOR=1` 关闭。
- 如需关闭本工具颜色，只设置 `KT_STATUSLINE_NO_COLOR=1`。

### Claude Code

- 写入 `statusLine`，调用本地无依赖 Python 渲染器。
- 默认显示：模型、effort、context、5h、weekly、Git 分支。
- 根据 context 和额度剩余自动显示红/黄/绿风险颜色。

### Codex CLI

- 写入 `[tui].status_line` 和 `status_line_use_colors = true`。
- 写入可公开、安全的常用偏好：
  - 默认模型、reasoning effort、verbosity、review model
  - approval / sandbox 策略
  - project doc fallback
  - history / shell env / agents
  - OpenAI curated plugins
  - context7 / playwright MCP servers

## 状态栏

默认效果：

```text
gpt-5.5 xhigh · Context 25% used · 5h 67% left · weekly 71% left · main
```

字段顺序：

```text
模型 effort · Context 已用百分比 · 5h 剩余百分比 · weekly 剩余百分比 · 当前 Git 分支
```

Claude Code 风险颜色：

| 字段 | 绿色 | 黄色 | 红色 |
| --- | --- | --- | --- |
| Context used | `< 60%` | `60-79%` | `>= 80%` |
| 5h / weekly left | `> 40%` | `21-40%` | `<= 20%` |

可选显示更多字段：

```bash
export KT_STATUSLINE_SHOW_CWD=1
export KT_STATUSLINE_SHOW_TOKENS=1
export KT_STATUSLINE_SHOW_COST=1
export KT_STATUSLINE_SHOW_VERSION=1
```

关闭本工具颜色：

```bash
export KT_STATUSLINE_NO_COLOR=1
```

## 操作资料

- [Warp 终端](docs/operations/warp.md)
- [Claude Code](docs/operations/claude-code.md)
- [Codex CLI](docs/operations/codex-cli.md)

## 本地开发

```bash
python3 scripts/install.py
python3 -m unittest
./bin/kt-aicoding-config doctor
```

检查 Codex 配置：

```bash
codex --strict-config --help
```

## 安全边界

这个仓库只提交可公开配置：

- 不提交 API token、provider key、OAuth token。
- 不提交个人机器上的项目 trust 列表。
- 不提交私有路径、私有业务上下文或大段个人开发者指令。
- 安装脚本只做增量写入，写入前自动备份。

## 资料来源

- Claude Code statusLine 文档：https://code.claude.com/docs/en/statusline
- Codex CLI config 文档：https://github.com/openai/codex/blob/main/docs/config.md
- Warp 环境变量文档：https://docs.warp.dev/knowledge-and-collaboration/warp-drive/environment-variables/
