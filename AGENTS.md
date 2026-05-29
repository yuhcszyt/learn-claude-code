# Agent 说明

## 项目概览

这个仓库是个人 AI 学习实验室，按主题分区组织：

- `claude-code/` 包含 Claude Code 风格 harness 工程课程、Python agent 示例、skills、tests 和 Web 学习站点。
- `langchain/` 预留给 LangChain / LangGraph 学习实验。
- `stock-research/` 包含 A 股研究工具、AKShare MCP 使用说明、本地研究脚本和报告输出目录。
- `shared/` 放跨主题复用的工具、模板和笔记。
- `docs/` 放仓库级路线图和索引；课程自己的文档在对应主题目录下。

## 环境

Python 依赖列在 `requirements.txt` 中：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Python 示例需要在 `.env` 中配置 API；可以使用 `.env.example` 作为模板。

Web 应用独立放在 `claude-code/web/` 下：

```powershell
cd claude-code/web
npm install
npm run dev
```

`npm run dev` 和 `npm run build` 会先运行 `npm run extract`，从课程内容重新生成 web 数据。

## 测试命令

从仓库根目录运行 Claude Code Python 冒烟测试：

```powershell
.\.venv\Scripts\python.exe -m pytest claude-code/tests
```

从 `claude-code/web/` 目录运行 web 检查：

```powershell
npm run build
```

## 编辑指导

- 学习者背景：用户有 Java 背景，正在学习 Python。解释或注释 Python 代码时，请指出 Python 特有的语法和惯用法；有帮助时，可以和 Java 概念做对比。
- 保持课程文件简单、可读；它们是教学材料，不是生产级框架。
- 对不太直观的 harness 机制，优先在附近添加简短说明性注释。
- 保持 `claude-code/s01_*` 到 `claude-code/s20_*` 的递进关系；避免把高级概念提前塞进早期课程。
- 避免手动修改 `claude-code/web/src/data/generated/` 下的生成文件。需要更新时，运行 `npm run extract` 重新生成。
- `stock-research/reports/`、`stock-research/data/`、`stock-research/cache/` 是生成产物目录，默认不要提交其中内容。
- 处理文件或代码搜索时，优先使用 CodeGraph；当需求语义模糊、CodeGraph 找不到相关内容，或需要核对原始文本时，再回退到 `rg`、文件读取等原生搜索工具。
- 工作树中可能包含用户改动。不要还原无关变更。

## 风格说明

- Python 示例优先追求清晰，而不是炫技。
- 现有文件注释可能包含中文说明；在已有注释块中补充内容时，保持注释简洁，并使用周围一致的语言。
- 任务或工具示例写入 JSON 时，通常使用 `ensure_ascii=False`，以便中文文本保持可读。
