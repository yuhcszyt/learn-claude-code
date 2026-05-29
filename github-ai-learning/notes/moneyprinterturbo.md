---
repo: https://github.com/harry0703/MoneyPrinterTurbo
status: reading
topics:
  - 短视频生成
  - AIGC
  - OpenAI兼容接口
  - Streamlit
  - FastAPI
tags:
  - github-ai-learning
  - video-generation
  - openai-compatible
---

# harry0703/MoneyPrinterTurbo

[[index|返回学习笔记索引]]

## 1. 为什么学这个项目

- 它解决什么问题：输入视频主题或关键词后，自动生成文案、素材、字幕、配音、背景音乐，并合成短视频。
- 和我当前路线的关系：它是一个完整的 AI 应用工作流样本，覆盖 WebUI、API、配置、多模型接入和多媒体处理。
- 我希望从里面学到什么：如何把 LLM、素材检索、TTS、字幕和视频合成组织成可运行产品。

## 2. 快速结论

- 可以用 `gpt-5.5`，前提是 OpenAI 账号有该模型权限。
- 项目默认走 OpenAI Chat Completions SDK，配置字段是 `openai_model_name`。
- 不建议使用不存在或非官方的模型名，例如 `chat5.5`；应使用官方模型 ID `gpt-5.5`。
- 视频生成还依赖 Pexels/Pixabay、ImageMagick、ffmpeg、TTS 和素材下载，LLM 只是其中一环。

## 3. 项目概览

- 技术栈：Python 3.11、Streamlit、FastAPI、MoviePy、OpenAI SDK、edge-tts、faster-whisper、ImageMagick、ffmpeg、Docker。
- 核心入口：
  - `webui/Main.py`：Streamlit Web 界面。
  - `main.py`：API 服务入口。
  - `app/services/llm.py`：多模型调用封装。
  - `config.example.toml`：服务商、模型、素材、字幕和运行配置。
- 运行方式：本地 `uv sync --frozen` 或 Docker。

## 4. GPT-5.5 配置方式

复制配置文件：

```bash
cp config.example.toml config.toml
```

在 `config.toml` 中设置：

```toml
llm_provider = "openai"
openai_api_key = "sk-..."
openai_base_url = ""
openai_model_name = "gpt-5.5"
```

如果通过 OpenAI 兼容网关使用，也可以设置网关地址：

```toml
llm_provider = "openai"
openai_api_key = "你的网关 key"
openai_base_url = "https://你的网关/v1"
openai_model_name = "网关要求的模型 ID"
```

## 5. macOS 快速启动

```bash
git clone https://github.com/harry0703/MoneyPrinterTurbo.git
cd MoneyPrinterTurbo
brew install imagemagick
uv python install 3.11
uv sync --frozen
cp config.example.toml config.toml
uv run streamlit run ./webui/Main.py --browser.gatherUsageStats=False
```

API 服务：

```bash
uv run python main.py
```

访问地址：

- WebUI：http://127.0.0.1:8501
- API docs：http://127.0.0.1:8080/docs

## 6. 和当前仓库的连接

- 可以补到 `shared/`：多模型 provider 配置模板、OpenAI 兼容接口封装。
- 可以补到 `claude-code/`：做一个“从 prompt 到多步骤媒体工作流”的教学案例。
- 可以补到 `github-ai-learning/`：继续精读视频生成 pipeline，包括脚本生成、素材检索、字幕和合成。

## 7. 下一步行动

- [ ] 精读 `app/services/llm.py`，确认不同 provider 的错误处理和兼容边界。
- [ ] 跑通 WebUI，只生成一个短视频样例。
- [ ] 记录 `gpt-5.5` 在脚本生成质量、速度和成本上的实际表现。
- [ ] 梳理视频生成 pipeline，画出从主题到成片的流程图。
