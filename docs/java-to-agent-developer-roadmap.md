# Java 转 Agent 开发学习目标

> 更新日期：2026-05-29  
> 目标定位：从 Java 后端开发转向企业级 Agent / 大模型应用开发，不走纯算法研究路线，优先补齐工程落地能力。

## 1. 岗位画像

从 Boss 直聘相关岗位和招聘需求汇总看，Java 转 Agent 开发最匹配的岗位通常不是“训练大模型算法岗”，而是下面三类：

1. 大模型应用开发工程师：负责 LLM 接入、RAG、Prompt、API 集成、知识库问答、智能客服、报告生成等业务落地。
2. AI Agent 应用开发工程师：负责 Agent 核心模块、工具调用、工作流编排、多 Agent 协作、业务流程自动化。
3. AI 平台 / 后端工程师：负责模型服务 API、权限、任务调度、日志观测、部署运维、稳定性和性能优化。

对 Java 背景最友好的切入点是“Agent 应用工程化”：继续使用 Spring Boot、数据库、缓存、消息队列、接口设计等后端优势，同时补上 LLM、RAG、工具调用、评估和安全。

## 2. Boss 岗位共性要求

| 岗位关键词 | 技术含义 | Java 转型要补的能力 |
| --- | --- | --- |
| Python / Java / Go 后端开发 | 至少掌握一门后端语言，能做 API 和工程集成 | Java 保持强项，补 Python 基础和脚本能力 |
| LLM / 大模型原理 | 理解模型调用、上下文窗口、token、幻觉、推理成本 | 能解释 LLM 应用边界，不必一开始会训练模型 |
| Prompt Engineering | 设计可复用、可测试、可约束的提示词 | 系统提示、工具提示、结构化输出、few-shot |
| RAG / 知识库 | 文档解析、切分、embedding、向量检索、重排、引用来源 | 做出一个可维护的企业知识库问答系统 |
| Agent / 工具调用 | 让模型选择工具、调用 API、读取数据、执行工作流 | 掌握 function calling、tool schema、权限控制 |
| LangChain / LangGraph / Dify / Coze | 主流 Agent 和工作流框架 | 以 Python LangChain / LangGraph 为主线；Dify / Coze / Langflow 作为平台化工具了解 |
| MCP | 标准化连接工具、资源和提示词 | 会写一个 MCP server，并接入本地工具或业务系统 |
| 多 Agent / Workflow | 拆任务、协作、审批、状态机、任务恢复 | 用 LangGraph 或自研 harness 实现可控流程 |
| Vector DB / 数据库 | MySQL、PostgreSQL、Redis、MongoDB、向量数据库 | 学 pgvector、Qdrant 或 Milvus 至少一种 |
| Docker / K8s / 云服务 | 部署、监控、扩缩容、私有化环境 | 能把 Agent 服务容器化并部署 |
| 模型微调 / LoRA / SFT | 加分项，部分岗位要求算法背景 | 先理解概念和适用场景，后续再实践 |
| 评估 / 监控 / 安全 | 质量评测、延迟、成本、越权、提示注入 | 会设计 eval case、日志追踪、权限边界 |

## 3. 我们的学习目标

### 第一阶段：Agent 工程基础

- 能讲清楚 Agent 的基本结构：模型、上下文、工具、记忆、计划、执行、反馈。
- 能写出最小 Agent loop：接收用户输入、调用模型、识别工具调用、执行工具、回传结果。
- 能理解 tool schema、request_id、消息队列、状态机这些后端熟悉概念在 Agent 里的对应关系。
- 能用当前仓库的 `claude-code/agents/` 课程解释每一课解决了什么工程问题。

### 第二阶段：Agent 应用栈选择

- Python LangChain / LangGraph：作为主线学习框架，负责 Agent、RAG、Workflow、多 Agent 编排。
- Python 脚本能力：用于数据处理、实验验证、MCP 工具、股票研究和快速原型。
- Spring Boot：继续作为 Java 后端强项，负责 API、权限、配置、任务调度、数据库访问。
- Spring AI：不进入近期主线；只在遇到明确 Java LLM 项目或面试问到时，了解它如何在 Spring Boot 中接入 Chat、Tools、RAG。
- LangChain4j：暂不学习；当前 Boss 岗位样本里没有看到它成为高频硬性要求。

### 第三阶段：RAG 和知识库

- 文档解析：Markdown、PDF、网页、代码文件。
- 文档切分：按标题、段落、token、语义块切分。
- 向量化：embedding 模型选择、维度、成本、缓存。
- 检索：top-k、相似度、混合检索、metadata filter。
- 重排：rerank、query rewrite、context compression。
- 可信回答：返回引用来源，承认不知道，避免编造。

### 第四阶段：工具调用和 MCP

- 能把普通后端 API 包装成模型可调用工具。
- 能设计工具权限：只读、写入、危险操作审批。
- 能处理工具调用失败：超时、重试、降级、错误消息。
- 能实现一个 MCP server，暴露 tools、resources、prompts。
- 能把 `stock-research/` 里的研究脚本接成 Agent 工具。

### 第五阶段：工作流和多 Agent

- 会区分自由 Agent 和受控 Workflow。
- 会用状态机管理审批、暂停、恢复、失败重试。
- 会设计多 Agent 协作：研究员、编码员、测试员、审阅员。
- 会记录任务上下文、执行轨迹、工具调用结果。
- 会用 eval case 验证 Agent 是否真的完成任务。

### 第六阶段：生产化能力

- API：REST / SSE / WebSocket，支持流式输出。
- 数据：MySQL / PostgreSQL / Redis / 对象存储 / 向量库。
- 部署：Docker Compose 起步，后续 K8s。
- 可观测性：请求日志、trace id、token 成本、延迟、错误率。
- 安全：提示注入、越权工具调用、敏感数据泄露、输出审查。
- 质量：离线评测、人工抽检、回归测试、灰度发布。

## 4. 仓库实践项目

| 项目 | 目标 | 放置位置 |
| --- | --- | --- |
| Claude Code harness 精读 | 理解 Agent loop、工具调用、团队协议、任务隔离 | `claude-code/` |
| Python LangChain Agent Demo | 用 LangChain / LangGraph 做一个可调用工具的 Agent 服务 | `langchain/examples/python-agent-demo/` |
| 个人知识库 RAG | 把本仓库学习笔记做成可问答知识库 | `langchain/projects/rag-notes/` |
| A 股研究 Agent | 让 Agent 拉数据、算指标、回测、生成报告、检查风险 | `stock-research/` |
| MCP 工具服务 | 把文件、股票研究、知识库检索包装成 MCP tools/resources | `shared/mcp/` |
| Agent 评估集 | 固定一组问题和期望行为，用来回归测试 Agent | `shared/evals/` |

## 5. 8 周学习路线

| 周次 | 学习重点 | 可交付物 |
| --- | --- | --- |
| 第 1 周 | 精读 `s01` 到 `s05`，理解 loop、tools、todo、subagent、skills | 每课写 1 页中文笔记 |
| 第 2 周 | 精读 `s06` 到 `s12`，理解压缩、任务系统、后台任务、团队协议、worktree | 画出 Agent 状态流转图 |
| 第 3 周 | Python LangChain / LangGraph 入门 | Python 调 LLM + tool calling demo |
| 第 4 周 | RAG 基础：文档解析、切分、embedding、检索 | 本仓库 README 问答系统 |
| 第 5 周 | RAG 进阶：重排、引用、评估、失败样例 | 20 条 RAG eval cases |
| 第 6 周 | MCP：tools、resources、prompts | 本地 MCP server demo |
| 第 7 周 | Workflow / 多 Agent：审批、状态机、失败恢复 | 研究员-审阅员双 Agent demo |
| 第 8 周 | 生产化：日志、成本、权限、安全、部署 | 可展示的 Agent 项目说明和架构图 |

## 6. 面试准备清单

- 能解释一个 Agent 请求从用户输入到工具执行再到最终回答的完整链路。
- 能解释 RAG 为什么能降低幻觉，但不能完全消除幻觉。
- 能比较纯 Prompt、RAG、Fine-tuning、Tool Calling 分别适合什么场景。
- 能讲清楚 Java 后端在 Agent 项目里的价值：稳定 API、权限、数据、任务调度、部署、观测。
- 能说明如何防止 Agent 误调用危险工具。
- 能设计一个企业知识库问答系统的表结构、向量库结构和 API。
- 能说明如何评估一个 Agent：准确率、引用命中率、任务完成率、延迟、成本、人工满意度。
- 能拿出至少两个作品：一个 RAG，一个工具调用 / MCP / Workflow Agent。

## 7. 参考来源

- [Boss 直聘岗位搜索：Java AI Agent](https://www.zhipin.com/web/geek/job?query=Java%20AI%20Agent)：用于观察 Java、Agent、大模型应用相关岗位关键词。
- [Boss 直聘岗位样本：大模型应用开发算法工程师](https://activity.zhipin.com/job_detail/a82a8bed8d53065703d-2NS0GVRT.html)：岗位摘要包含 Agent 应用开发、RAG、Python/Java、工程能力、架构设计与优化。
- [Boss 直聘岗位搜索：大模型应用开发工程师](https://www.zhipin.com/web/geek/job?query=%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91%E5%B7%A5%E7%A8%8B%E5%B8%88)：用于观察 RAG、流程编排、LLM 调优、LangChain / LlamaIndex 等要求。
- [LangChain 官方文档](https://python.langchain.com/docs/introduction/)：Python 侧 LLM 应用、Tools、RAG、Agent 基础。
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)：Python 侧可控 Agent Workflow、状态图、多 Agent 编排。
- [Spring AI 官方文档](https://docs.spring.io/spring-ai/reference/)：Java LLM 应用组件，暂列为需要时再查的补充资料。
- [LangChain4j 官方文档](https://docs.langchain4j.dev/)：Java 原生 LLM 应用框架，暂不进入近期学习计划。
- [MCP 官方文档](https://modelcontextprotocol.io/docs/getting-started/intro)：tools、resources、prompts、能力发现和工具调用协议。

## 8. 下一步

短期先不要贪多。建议先把当前仓库当成作品集底座：

1. 继续学完 `claude-code/agents/`，把 Agent loop 和工具调用吃透。
2. 在 `langchain/` 下先新建 Python LangChain / LangGraph demo，把 Agent、RAG、Workflow 跑通。
3. 把 `stock-research/` 接成真实工具调用场景，形成一个比普通聊天机器人更有说服力的作品。
