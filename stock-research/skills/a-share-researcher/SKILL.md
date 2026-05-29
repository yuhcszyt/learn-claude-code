---
name: a-share-researcher
description: Provides an A-share research workflow using akshare-one-mcp and the local research CLI. Use when the user asks to analyze A-shares, pull China stock data, calculate indicators, backtest a strategy, generate a report, or check strategy risk.
---

# A-Share Researcher

## Quick Start

Use the MCP server for ad hoc data lookup:

```bash
uvx akshare-one-mcp
```

Use the local CLI for repeatable research reports:

```bash
uv run --with akshare --with pandas --with numpy python stock-research/tools/a_share_researcher.py 600519 --start 20240101 --end 20260529
```

Outputs are written under `stock-research/reports/<symbol>_<timestamp>/`.

## Workflow

1. Pull daily A-share data with forward-adjusted prices by default.
2. Calculate indicators: SMA, EMA, MACD, RSI, Bollinger Bands, ATR, volume average, drawdown.
3. Run a simple long-only moving-average crossover backtest.
4. Generate CSV artifacts and a Markdown report.
5. Check strategy risk before presenting conclusions.

## Report Rules

Always treat the result as research, not financial advice. Mention:

- Data source and date range.
- Strategy assumptions, including no intraday execution and approximate fees.
- Return, drawdown, volatility, Sharpe, win rate, exposure, trade count, and turnover.
- Risk warnings for small samples, high drawdown, low trade count, high turnover, and weak risk-adjusted return.
- Next validation steps before any live use.

## Useful Prompts

- `分析 600519，最近三年，生成 A 股研究报告`
- `用 20/60 日均线回测 000001，检查风险`
- `拉取 300750 的日线数据，计算 MACD/RSI/布林带并输出报告`
