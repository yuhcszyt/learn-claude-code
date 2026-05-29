# Learning Lab

This repository is a personal learning lab for agent engineering, LLM application frameworks, and market research tooling.

## Areas

- `claude-code/` - Claude Code style harness engineering course material, runnable Python agents, skills, tests, and the learning website.
- `langchain/` - reserved workspace for LangChain and LangGraph experiments.
- `github-ai-learning/` - study notes for GitHub AI projects, including source reading, reproduction notes, and reusable takeaways.
- `stock-research/` - A-share research tooling with `akshare-one-mcp`, repeatable Python reports, and risk checks.
- `shared/` - cross-topic utilities, templates, and notes that do not belong to a single learning area.
- `docs/` - repository-level learning roadmap and index.

## Quick Start

Claude Code course:

```powershell
python claude-code/s01_agent_loop/code.py
```

A-share research script:

```powershell
uv run --with akshare --with pandas --with numpy python stock-research/tools/a_share_researcher.py 600519 --start 20240101 --end 20260529
```

Web course site:

```powershell
cd claude-code/web
npm run dev
```

## Repository Policy

Track source code, prompts, templates, and learning notes. Ignore generated reports, market data exports, caches, IDE state, and runtime mailboxes.
