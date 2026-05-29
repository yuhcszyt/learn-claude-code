# GitHub AI 项目学习

这个目录专门记录从 GitHub AI 项目中学到的东西。目标不是收藏链接，而是把每次学习变成可复盘的工程笔记：

- 项目解决什么问题。
- 架构和关键模块怎么组织。
- 值得借鉴的代码、提示词、工具协议或工程实践。
- 和自己当前学习路线的关系。
- 下一步要复现、改造或迁移到本仓库的动作。

## 使用方式

1. 发现一个值得学习的 GitHub 项目。
2. 复制 `templates/project-study.md` 到 `records/YYYY-MM-DD-project-name.md`。
3. 按模板记录阅读过程、关键文件、运行步骤和收获。
4. 在 `index.md` 增加一行索引。
5. 如果产生可复用代码或实验，放到对应主题目录，例如 `langchain/`、`claude-code/`、`stock-research/` 或 `shared/`。

## 推荐记录粒度

一次记录只聚焦一个项目，或者一个项目里的一个明确主题。比如：

- `LangGraph` 的状态图和 checkpoint。
- `AutoGen` 的多 Agent 对话模式。
- `OpenHands` 的工具执行和沙箱。
- `Dify` 的 workflow 节点设计。
- 某个 RAG 项目的文档切分和引用来源实现。

## 目录结构

- `index.md` - 学习记录索引。
- `records/` - 每次项目学习的正式笔记。
- `templates/` - 记录模板。
- `watchlist.md` - 候选项目清单，还没开始深入学习。
