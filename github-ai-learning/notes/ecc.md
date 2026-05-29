---
repo: https://github.com/affaan-m/ECC
status: reading
topics:
  - Codex
  - Claude Code
  - Skills
  - MCP
  - 工具配置
tags:
  - github-ai-learning
  - codex
  - mcp
---

# affaan-m/ECC

[[index|返回学习笔记索引]]

## 仓库链接

- https://github.com/affaan-m/ECC

## 为什么值得看

ECC 不是一个普通代码库，而是一个跨 AI 编码工具的配置和工作流包。它把 Codex、Claude Code、Cursor、OpenCode、Gemini、Zed、GitHub Copilot 等工具的规则、skills、MCP、提示词和多代理配置尽量统一到一套工程实践里。

对学习 Codex/agent 工程比较有价值，因为它展示了一个核心思路：AI 工具的能力不只来自模型本身，还来自外部约束、技能说明、项目级 AGENTS.md、MCP 工具、验证流程和安全边界。

## 核心结构

- `.codex-plugin/plugin.json`：Codex 插件声明，定义插件名、版本、skills 目录、MCP 配置和默认提示。
- `.codex/config.toml`：Codex 参考配置，包含审批策略、沙箱模式、MCP servers、multi-agent 配置和 profiles。
- `.codex/AGENTS.md`：Codex 专用补充说明。
- `.codex/agents/`：Codex 多代理角色配置，例如 explorer、reviewer、docs-researcher。
- `skills/`：大量可复用 skill，每个 skill 通常围绕一个具体工作流。
- `scripts/sync-ecc-to-codex.sh`：把 ECC 同步到本机 Codex 全局配置的脚本。
- `.mcp.json` / `mcp-configs/`：MCP server 配置。

## 安装判断

可以装到 Codex，但要分清两种安装级别：

1. 项目级使用：只把需要的 `AGENTS.md`、`.codex/`、少量 skills 或 rules 放到当前项目。这种方式更透明，影响范围小。
2. 全局同步：运行 `scripts/sync-ecc-to-codex.sh` 或类似安装流程，会改 `~/.codex/config.toml`、`~/.codex/AGENTS.md`、prompts、MCP server，并安装全局 git safety hooks。这种方式影响所有 Codex 会话，应该先 dry-run 和备份。

当前更适合先项目级学习，不建议直接全局安装全部 ECC。

## 可复用技巧

- 用 `AGENTS.md` 做跨工具的统一行为约束。
- 用 `.codex/config.toml` 明确审批策略、沙箱、MCP、multi-agent 角色。
- 把复杂工作流拆成 skills，而不是把所有规则塞进一个超长系统提示词。
- 对全局安装脚本做 marker-based merge 和 backup，降低覆盖用户配置的风险。
- 用 dry-run 模式预览安装计划，这是 agent 配置包很值得借鉴的安全设计。

## 快速开始

先不要全局安装。建议学习路径：

1. 阅读 `.codex-plugin/plugin.json`，理解 Codex 插件如何声明 skills 和 MCP。
2. 阅读 `.codex/config.toml`，看 Codex 如何配置 sandbox、approval、MCP 和 agents。
3. 阅读 `scripts/sync-ecc-to-codex.sh`，重点看它改了哪些全局位置。
4. 挑 2 到 3 个 skill 学，例如 `tdd-workflow`、`security-review`、`verification-loop`。
5. 如果真要安装，先跑 dry-run，再决定是否全局写入。

## 对当前仓库的启发

当前仓库是学习 Claude Code / Codex agent 原理的教程仓库，更适合保留“手搓透明”的风格。ECC 的价值不是直接照搬全部配置，而是学习它如何组织规则、skills、MCP 和安装边界。

最值得迁移的是：

- 给 agent 教程增加更清楚的安装边界说明。
- 对会写入用户全局配置的脚本强制 dry-run。
- 把“任务规划、验证、安全检查”拆成小而明确的教程章节。
