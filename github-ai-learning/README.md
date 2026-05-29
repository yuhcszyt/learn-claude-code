---
type: guide
tags:
  - github-ai-learning
  - obsidian
---

# GitHub AI 项目学习

这个目录可以直接作为 Obsidian vault 打开。入口是 [[index|GitHub AI 项目学习笔记]]。

目标不是收藏链接，而是把每次学习沉淀进同一份持续维护的工程笔记：

- 项目解决什么问题。
- 架构和关键模块怎么组织。
- 值得借鉴的代码、提示词、工具协议或工程实践。
- 和自己当前学习路线的关系。
- 下一步要复现、改造或迁移到本仓库的动作。

## 使用方式

1. 发现一个值得学习的 GitHub 项目。
2. 如果 `notes/project-name.md` 已存在，直接更新它。
3. 如果不存在，复制 [[templates/project-study|项目学习笔记模板]] 到 `notes/project-name.md`。
4. 在 [[index|学习笔记索引]] 增加一条 `[[notes/project-name|项目名]]` 双链。
5. 如果产生可复用代码或实验，放到对应主题目录，例如 `langchain/`、`claude-code/`、`stock-research/` 或 `shared/`。

## Obsidian 约定

- 使用 YAML frontmatter 存 `repo`、`status`、`topics` 和 `tags`。
- 使用 `[[双链]]` 连接索引、候选清单和项目笔记。
- 一份笔记对应一个项目，后续学习继续维护同一个文件。
- 文件名使用稳定 slug，例如 `moneyprinterturbo.md`，不要按日期命名。

## 目录结构

- [[index|index.md]] - 学习笔记 MOC。
- `notes/` - 按项目持续维护的正式学习笔记。
- `templates/` - 笔记模板。
- [[watchlist|watchlist.md]] - 候选项目清单。
