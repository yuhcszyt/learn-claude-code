# Repository Guidelines

## Project Structure & Module Organization

This repository is a learning lab split by topic:

- `claude-code/`: Claude Code course material, runnable Python agents, tests, and the web learning site.
- `claude-code/web/`: Next.js app that renders generated course content.
- `github-ai-learning/`: study notes for GitHub repositories and reusable takeaways.
- `stock-research/`: A-share research scripts, reports, and related tooling.
- `langchain/`, `shared/`, `docs/`: experiments, shared utilities/templates, and repo-level docs.

Keep generated output out of version control where possible, especially under `stock-research/reports/`, `stock-research/data/`, and caches.

## Build, Test, and Development Commands

- Python environment: `python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt`
- Run Python smoke tests: `./.venv/Scripts/python -m pytest claude-code/tests`
- Start the first course example: `python claude-code/s01_agent_loop/code.py`
- Web app dev server: `cd claude-code/web && npm install && npm run dev`
- Web app production check: `cd claude-code/web && npm run build`

Mac quick start:

- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `cd claude-code/web && npm install && npm run dev`

`npm run dev` and `npm run build` trigger `npm run extract` first, which regenerates web content data.

## Coding Style & Naming Conventions

- Prefer small, readable teaching examples over abstraction-heavy code.
- Follow existing naming patterns such as `s01_*`, `s02_*` in `claude-code/`.
- Use 4 spaces for Python and keep comments concise.
- Do not manually edit generated files under `claude-code/web/src/data/generated/`.

## Testing Guidelines

- Python tests use `pytest`; place tests in `claude-code/tests/` as `test_*.py`.
- Prefer targeted smoke tests for learning examples before broader validation.
- For web changes, run `npm run build` as the minimum verification step.

## Commit & Pull Request Guidelines

- Follow the existing commit style: Conventional Commit-like prefixes such as `docs:`, `chore:`, `fix:`.
- Keep commits focused on one topic area.
- PRs should include scope, key files changed, validation commands run, and screenshots for UI changes.

## GitHub Learning Notes

- When a user sends a GitHub repository for learning, evaluation, or comparison, first answer the user's learning request directly.
- Do not automatically create Obsidian study notes for every repository discussion. After answering, ask whether the user wants a study note generated.
- Create or update notes in `github-ai-learning/` only when the user explicitly asks for notes or confirms after being asked.
- When creating notes, treat `github-ai-learning/` as an Obsidian vault: use `index.md` as the MOC, `[[wikilinks]]` for navigation, and YAML frontmatter for metadata.
- Use one stable file per project in `github-ai-learning/notes/project-name.md`; update the same note on later visits instead of creating date-based duplicates.
- Update `github-ai-learning/index.md` only when adding a new project note.
- Each note should include: repository link, why it matters, core ideas, reusable techniques, and a fast start section for macOS.
