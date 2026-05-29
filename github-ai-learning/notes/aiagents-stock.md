---
repo: https://github.com/oficcejo/aiagents-stock
status: reading
topics:
  - A股研究
  - 多智能体
  - Streamlit
  - 量化辅助
  - 监控通知
tags:
  - github-ai-learning
  - ai-agents
  - stock-research
---

# oficcejo/aiagents-stock

[[index|返回学习笔记索引]]

## 1. 为什么学这个项目

- 它解决什么问题：把 A 股行情、资金流、龙虎榜、宏观、新闻、风险事件等数据接入多个 AI 分析师角色，生成股票分析、监控提醒和报告。
- 和我当前路线的关系：它正好连接 `stock-research/`、Agent 工程和 GitHub AI 项目精读，是“AI + A 股研究”的实战样本。
- 我希望从里面学到什么：多智能体分析流程、股票数据采集链路、报告生成、监控通知、交易接口预留方式。

## 2. 快速结论

- 最重要的收获：它是一个功能堆得很完整的 A 股 AI 研究工作台，适合作为需求地图和模块拆解参考。
- 最值得借鉴的设计：按数据采集、分析师角色、综合决策、报告导出、监控通知拆模块。
- 暂时不需要照搬的部分：自动交易、实盘推荐、过多策略参数和未经验证的“收益率”描述。

## 3. 项目概览

- 技术栈：Python、Streamlit、DeepSeek/OpenAI 兼容接口、AKShare、pywencai、yfinance、TA-Lib、Plotly、SQLite、Docker。
- 核心模块：
  - `app.py`：Streamlit 主界面。
  - `ai_agents.py`：股票分析师团队。
  - `deepseek_client.py`：OpenAI 兼容模型调用。
  - `longhubang_*`：龙虎榜数据、分析、评分、报告和 UI。
  - `sector_strategy_*`：板块轮动和策略分析。
  - `monitor_*`：价格监控、调度和通知。
  - `miniqmt_interface.py`：MiniQMT 交易接口预留。
- 运行方式：README 推荐 Docker，也支持本地 `pip install -r requirements.txt` 后运行。

## 4. 架构拆解

| 模块 | 职责 | 我需要关注的文件 |
| --- | --- | --- |
| 多智能体分析 | 技术面、基本面、资金面、风险、情绪、新闻分析，再做团队讨论和最终决策 | `ai_agents.py`、`deepseek_client.py` |
| A 股数据源 | AKShare、问财、TDX、Tushare 降级链路 | `data_source_manager.py`、`fund_flow_akshare.py`、`main_force_selector.py` |
| 龙虎榜分析 | 游资行为、题材追踪、风险控制、首席策略 | `longhubang_agents.py`、`longhubang_engine.py`、`longhubang_scoring.py` |
| 板块策略 | 宏观、板块、资金、情绪多 Agent 分析 | `sector_strategy_agents.py`、`sector_strategy_engine.py` |
| 监控通知 | 价格区间、止盈止损、定时任务、邮件/Webhook | `monitor_service.py`、`monitor_scheduler.py`、`notification_service.py` |
| 报告生成 | Markdown、HTML、PDF、CSV 导出 | `pdf_generator.py`、`main_force_pdf_generator.py`、`sector_strategy_pdf.py` |

## 5. 关键观察

### 多智能体不是复杂框架，而是“角色化 Prompt + 顺序编排”

- `ai_agents.py` 中每个分析师函数负责构造领域提示词，并调用同一个模型客户端。
- 最后通过团队讨论 prompt 汇总各分析师报告，再让模型给最终决策。
- 这对学习很友好：可以先在 `stock-research/` 里复刻一个轻量版本，不必一开始引入 LangGraph。

### 数据源比 Agent 更关键

- 项目价值不只在 AI，而在接入了 AKShare、问财、TDX、新闻、财报、风险事件等多源数据。
- 对 A 股来说，数据稳定性、字段清洗、失败降级，比“模型说得像专家”更重要。
- 我们自己的 `stock-research/` 应该优先沉淀可复跑的数据层和指标层。

### 风险点要单独建模

- 项目把限售解禁、股东减持、重要事件、市场风险等单独交给风险分析师。
- 这个方向值得学：不要让“推荐买入”覆盖掉风险说明。
- 后续可在本仓库增加 `risk_check`，输出仓位建议、止损、数据缺失风险。

### 自动交易必须谨慎

- 项目有 MiniQMT 接口和自动交易描述，但这部分不适合直接照搬。
- 学习重点应该是接口边界、模拟交易、人工确认、日志和风控，而不是让模型直接下单。

## 6. 可迁移到本仓库的实践

- `stock-research/tools/a_share_researcher.py` 可以扩展成“数据采集 -> 指标计算 -> 多角色分析 -> 风险检查 -> Markdown 报告”的管线。
- 新增轻量多智能体角色：技术分析师、资金分析师、风险分析师、总结师。
- 把报告格式标准化：结论、证据、风险、数据缺失、下一步观察。
- 为每次研究保存结构化 JSON，便于后续回测和比较模型输出。
- 先做“研究辅助”和“模拟决策”，不碰实盘自动交易。

## 7. 不足和风险

- README 功能非常多，代码文件也很多，可能存在功能堆叠和维护边界不清的问题。
- 仓库包含 `.db` 文件和大量业务脚本，学习时要区分“可复用架构”和“个人策略实现”。
- 投资收益描述不能当作可靠依据，需要自己用历史数据回测和风险指标验证。
- 数据源依赖第三方免费接口，稳定性和合规性都要谨慎。
- AI 输出只能作为研究辅助，不能直接作为投资建议。

## 8. 下一步行动

- [ ] 精读 `ai_agents.py` 的分析师编排，画出多智能体调用流程。
- [ ] 精读 `deepseek_client.py`，学习 OpenAI 兼容模型调用封装。
- [ ] 精读一个数据模块，例如 `main_force_selector.py` 或 `sector_strategy_data.py`。
- [ ] 在 `stock-research/` 复刻一个更小的 A 股多角色研究管线。
- [ ] 增加风险声明和人工确认机制，避免模型输出被误当成交易指令。
