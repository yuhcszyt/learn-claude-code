# Stock Research Workspace

This folder is for A-share research experiments powered by `akshare-one-mcp` and local Python scripts.

## Layout

- `tools/` - repeatable research scripts.
- `skills/` - local agent workflow notes for A-share research.
- `reports/` - generated reports, CSVs, and backtest artifacts.
- `data/` - local market data exports.
- `cache/` - temporary caches.

## MCP Setup

The repository-level `.mcp.json` registers `akshare-one-mcp` so Codex and compatible MCP clients can discover it from the repo root.

`akshare-one-mcp` has been verified with:

```powershell
uvx akshare-one-mcp --help
```

To run it as an MCP stdio server:

```powershell
uvx akshare-one-mcp
```

To run it as an HTTP MCP server:

```powershell
uvx akshare-one-mcp --streamable-http --host 127.0.0.1 --port 8081
```

## Research CLI

Run a complete research pass:

```powershell
uv run --with akshare --with pandas --with numpy python stock-research/tools/a_share_researcher.py 600519 --start 20240101 --end 20260529
```

The script fetches daily A-share data, calculates indicators, runs a simple moving-average backtest, writes CSV artifacts, and generates a Markdown risk report under `stock-research/reports/`.

This is research tooling only. It does not place orders and does not provide financial advice.
