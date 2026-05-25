# Agent 说明

## 项目概览

这个仓库用于讲解 Claude Code 风格的 harness 工程。核心示例位于 `agents/`，是一组逐步丰富的 Python 脚本：

- `s01_agent_loop.py` 到 `s12_worktree_task_isolation.py` 是适合单课讲解的 harness 实现。
- `s_full.py` 将这些模式组合成一个更完整的参考实现。
- `openai_compat.py` 将示例适配到 OpenAI 兼容的 chat/message 客户端。
- `skills/` 包含技能加载课程中使用的本地 skill 示例。
- `docs/zh/` 包含中文课程文档。
- `web/` 是一个 Next.js 学习站点，用于渲染文档、源码注释、场景和可视化内容。

## 环境

Python 依赖列在 `requirements.txt` 中：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Python 示例需要在 `.env` 中配置 API；可以使用 `.env.example` 作为模板。

Web 应用独立放在 `web/` 下：

```powershell
cd web
npm install
npm run dev
```

`npm run dev` 和 `npm run build` 会先运行 `npm run extract`，从课程内容重新生成 web 数据。

## 测试命令

从仓库根目录运行 Python 冒烟测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

从 `web/` 目录运行 web 检查：

```powershell
npm run build
```

## 编辑指导

- 学习者背景：用户有 Java 背景，正在学习 Python。解释或注释 Python 代码时，请指出 Python 特有的语法和惯用法；有帮助时，可以和 Java 概念做对比。
- 保持课程文件简单、可读；它们是教学材料，不是生产级框架。
- 对不太直观的 harness 机制，优先在附近添加简短说明性注释。
- 保持 `s01` 到 `s12` 的递进关系；避免把高级概念提前塞进早期课程。
- 避免手动修改 `web/src/data/generated/` 下的生成文件。需要更新时，运行 `npm run extract` 重新生成。
- 处理文件或代码搜索时，优先使用 CodeGraph；当需求语义模糊、CodeGraph 找不到相关内容，或需要核对原始文本时，再回退到 `rg`、文件读取等原生搜索工具。
- 工作树中可能包含用户改动。不要还原无关变更。

## 风格说明

- Python 示例优先追求清晰，而不是炫技。
- 现有文件注释可能包含中文说明；在已有注释块中补充内容时，保持注释简洁，并使用周围一致的语言。
- 任务或工具示例写入 JSON 时，通常使用 `ensure_ascii=False`，以便中文文本保持可读。

