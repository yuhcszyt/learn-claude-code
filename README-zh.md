# 学习实验室

这个仓库现在是一个个人学习实验室，用来长期沉淀 Agent 工程、LLM 应用框架、量化/股票研究工具。

## 主题分区

- `claude-code/` - Claude Code 风格 harness 工程课程、可运行 Python agent、skills、测试和学习网站。
- `langchain/` - LangChain / LangGraph 学习实验区。
- `github-ai-learning/` - GitHub AI 项目精读记录，用来沉淀源码阅读、复现和迁移笔记。
- `stock-research/` - A 股研究工具区，包含 `akshare-one-mcp`、可复跑研究脚本、报告和风险检查。
- `shared/` - 跨主题复用的工具、模板和笔记。
- `docs/` - 仓库级学习路线图和索引。

## 快速开始

Claude Code 课程：

```powershell
python claude-code/s01_agent_loop/code.py
```

A 股研究脚本：

```powershell
uv run --with akshare --with pandas --with numpy python stock-research/tools/a_share_researcher.py 600519 --start 20240101 --end 20260529
```

课程网站：

```powershell
cd claude-code/web
npm run dev
```

## 仓库规则

代码、提示词、模板和学习笔记进入版本管理。生成报告、行情 CSV、缓存、IDE 状态和运行态邮箱默认忽略。
