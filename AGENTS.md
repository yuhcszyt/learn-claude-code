# Agent Notes

## Project Overview

This repository teaches Claude Code-style harness engineering. The core examples live in `agents/` as progressively richer Python scripts:

- `s01_agent_loop.py` through `s12_worktree_task_isolation.py` are lesson-sized harness implementations.
- `s_full.py` combines the patterns into one larger reference implementation.
- `openai_compat.py` adapts the examples to OpenAI-compatible chat/message clients.
- `skills/` contains local skill examples used by the skill-loading lessons.
- `docs/zh/` contains Chinese lesson documentation.
- `web/` is a Next.js learning site that renders docs, source annotations, scenarios, and visualizations.

## Environment

Python dependencies are listed in `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The Python examples expect API configuration in `.env`; use `.env.example` as the template.

The web app is isolated under `web/`:

```powershell
cd web
npm install
npm run dev
```

`npm run dev` and `npm run build` run `npm run extract` first, which regenerates generated web data from the lesson content.

## Test Commands

Run Python smoke tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run web checks from `web/`:

```powershell
npm run build
```

## Editing Guidance

- Learner context: the user is learning Python from a Java background. When explaining or annotating Python code, call out Python-specific syntax and idioms, and compare them to Java concepts when helpful.
- Keep lesson files simple and readable; they are teaching artifacts, not production frameworks.
- Prefer small explanatory comments near non-obvious harness mechanics.
- Preserve the progression across `s01` to `s12`; avoid moving advanced concepts into early lessons.
- Avoid changing generated files under `web/src/data/generated/` by hand. Regenerate them with `npm run extract`.
- The working tree may contain user edits. Do not revert unrelated changes.

## Style Notes

- Python examples target clarity over cleverness.
- Existing file comments may include Chinese explanations; keep comments concise and use the surrounding language when adding to a commented block.
- JSON written by task/tool examples usually uses `ensure_ascii=False` so Chinese text remains readable.
