---
repo: https://github.com/D4Vinci/Scrapling
status: reading
topics:
  - Python
  - Web Scraping
  - MCP
  - AI Agent
  - 数据抓取
tags:
  - github-ai-learning
  - python
  - scraping
  - mcp
---

# D4Vinci/Scrapling

[[index|返回学习笔记索引]]

## 仓库链接

- https://github.com/D4Vinci/Scrapling
- 文档：https://scrapling.readthedocs.io

## 为什么值得看

Scrapling 是一个现代 Python 网页抓取框架，定位不是单纯替代 requests 或 BeautifulSoup，而是把请求、解析、动态浏览器、反爬处理、Spider 爬虫、CLI 和 AI/MCP 集成放在一套工具里。

对当前学习路线有价值，因为它刚好连接了两个方向：

- Python 工程能力：请求、异步、解析、CLI、测试、包管理。
- AI Agent 工具能力：网页资料抓取、结构化抽取、MCP server、给 Codex/Claude/Cursor 当外部工具。

如果以后要做“让 Codex 自动调研网页、提取资料、整理成笔记”的工具，Scrapling 是一个值得参考的底层库。

## 核心能力

- `Fetcher`：普通 HTTP 抓取，适合静态网页和轻量请求。
- `StealthyFetcher`：更强的反爬和浏览器指纹伪装，适合被 Cloudflare 等保护的网站。
- `DynamicFetcher`：基于浏览器自动化抓动态页面，适合需要 JavaScript 渲染的页面。
- `Spider`：类似 Scrapy 的爬虫框架，支持 `start_urls`、异步 `parse`、并发、暂停和恢复。
- CSS/XPath/BeautifulSoup 风格选择器：可以用熟悉的方式从页面里提取内容。
- Adaptive scraping：网页结构变化后，尝试根据相似度重新定位元素。
- CLI：可以用 `scrapling shell` 或 `scrapling extract` 直接在终端抓取。
- MCP server：可以作为 AI 工具接入 Claude、Cursor、Codex 一类 agent 环境。
- `agent-skill/`：仓库里还提供了面向 AI agent 的 skill 入口。

## 和 Codex 怎么配合

更推荐分两步走：

1. 先作为普通 Python 库使用，让 Codex 写明确的抓取脚本。
2. 再考虑接 MCP，让 Codex 把 Scrapling 当成外部抓网页工具。

普通脚本方式最透明：

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://quotes.toscrape.com/")
quotes = page.css(".quote .text::text").getall()
print(quotes)
```

MCP 方式适合工具化：

```bash
pip install "scrapling[ai]"
```

然后把 Scrapling 的 MCP server 接进 Codex 配置。这样 Codex 可以调用工具抓页面、抽内容，再把结果放进上下文，而不是把完整网页 HTML 全塞给模型。

## 快速开始

最小安装：

```bash
pip install scrapling
```

如果要用 fetcher、浏览器、反爬能力：

```bash
pip install "scrapling[fetchers]"
scrapling install
```

如果要用 MCP：

```bash
pip install "scrapling[ai]"
```

如果要全部功能：

```bash
pip install "scrapling[all]"
scrapling install
```

## 可复用技巧

- 把网页抓取能力封装成清晰工具，而不是让 LLM 直接读巨大 HTML。
- 对静态网页、动态网页、反爬网页分别提供不同 fetcher，接口统一但能力分层。
- Spider 支持 pause/resume，说明长任务爬取需要状态持久化。
- Adaptive selector 是一个有意思的思路：选择器不只是一段字符串，也可以被记录、匹配和恢复。
- MCP server 可以降低 token 消耗：先在工具侧提取目标内容，再把小结果交给 LLM。

## 风险和边界

- 抓取网页要遵守网站条款、robots.txt 和当地法律。
- 反爬能力很强，但不能把它理解成“任何网站都可以随便抓”。
- 浏览器依赖较重，`scrapling install` 会安装浏览器和相关依赖，适合隔离环境或 Docker。
- MCP 接入前应该先用普通脚本跑通，避免一上来就把问题混在 Codex 配置、Python 环境和浏览器依赖里。

## 对当前仓库的启发

当前仓库在学习 agent loop 和工具调用。Scrapling 可以作为一个很好的后续实践：

- 做一个 `web_extract` 工具：输入 URL 和 CSS selector，输出结构化文本。
- 做一个“GitHub README 学习助手”：抓 README、提取安装方式、技术栈和使用场景。
- 做一个 Codex MCP 实验：让 agent 调 Scrapling 抓网页，再生成 Obsidian 笔记。

这类实践能把“手搓 agent 工具调用”和“真实世界网页数据获取”接起来。
