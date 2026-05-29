from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TRADING_DAYS = 252


@dataclass
class BacktestResult:
    metrics: dict[str, float | int | str]
    trades: pd.DataFrame
    equity: pd.Series
    position: pd.Series
    net_returns: pd.Series


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A-share research CLI: fetch data, calculate indicators, backtest, and write a Markdown report."
    )
    parser.add_argument("symbol", help="A-share code, for example 600519 or 000001")
    parser.add_argument("--start", default="20240101", help="Start date, YYYYMMDD")
    parser.add_argument("--end", default=datetime.now().strftime("%Y%m%d"), help="End date, YYYYMMDD")
    parser.add_argument("--adjust", default="qfq", choices=["qfq", "hfq", ""], help="Adjustment: qfq, hfq, or empty")
    parser.add_argument("--fast", type=int, default=20, help="Fast SMA window")
    parser.add_argument("--slow", type=int, default=60, help="Slow SMA window")
    parser.add_argument("--initial-capital", type=float, default=100000.0, help="Initial capital")
    parser.add_argument("--fee-bps", type=float, default=5.0, help="One-way transaction cost in basis points")
    parser.add_argument("--output-dir", default="stock-research/reports", help="Output directory root")
    return parser.parse_args()


def fetch_daily_data(symbol: str, start: str, end: str, adjust: str) -> pd.DataFrame:
    import akshare as ak

    raw = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start,
        end_date=end,
        adjust=adjust,
    )
    if raw.empty:
        raise ValueError(f"No data returned for {symbol} from {start} to {end}.")

    column_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude_pct",
        "涨跌幅": "change_pct",
        "涨跌额": "change_amount",
        "换手率": "turnover_pct",
    }
    data = raw.rename(columns=column_map)
    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [name for name in required if name not in data.columns]
    if missing:
        raise ValueError(f"Missing expected columns from data source: {missing}")

    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").set_index("date")
    numeric_columns = [col for col in data.columns if col != "date"]
    data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return data.dropna(subset=["open", "high", "low", "close"])


def calculate_indicators(data: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    df = data.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]

    df[f"sma_{fast}"] = close.rolling(fast).mean()
    df[f"sma_{slow}"] = close.rolling(slow).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["boll_mid"] = mid
    df["boll_upper"] = mid + 2 * std
    df["boll_lower"] = mid - 2 * std

    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = true_range.rolling(14).mean()
    df["volume_sma_20"] = df["volume"].rolling(20).mean()
    df["daily_return"] = close.pct_change()
    df["drawdown"] = close / close.cummax() - 1
    return df


def run_ma_backtest(
    data: pd.DataFrame,
    fast: int,
    slow: int,
    initial_capital: float,
    fee_bps: float,
) -> BacktestResult:
    close = data["close"]
    signal = (data[f"sma_{fast}"] > data[f"sma_{slow}"]).astype(float)
    position = signal.shift(1).fillna(0.0)
    raw_returns = close.pct_change().fillna(0.0)
    turnover = position.diff().abs().fillna(position.abs())
    fee_rate = fee_bps / 10000
    net_returns = position * raw_returns - turnover * fee_rate
    equity = initial_capital * (1 + net_returns).cumprod()

    trades = extract_trades(close, position, fee_rate)
    metrics = calculate_metrics(
        raw_returns=raw_returns,
        net_returns=net_returns,
        equity=equity,
        position=position,
        turnover=turnover,
        trades=trades,
        initial_capital=initial_capital,
        fee_bps=fee_bps,
    )
    return BacktestResult(metrics=metrics, trades=trades, equity=equity, position=position, net_returns=net_returns)


def extract_trades(close: pd.Series, position: pd.Series, fee_rate: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    entry_date = None
    entry_price = None

    for date, pos in position.items():
        prev_pos = position.shift(1).loc[date]
        prev_pos = 0 if pd.isna(prev_pos) else prev_pos
        price = float(close.loc[date])
        if prev_pos == 0 and pos > 0:
            entry_date = date
            entry_price = price
        elif prev_pos > 0 and pos == 0 and entry_date is not None and entry_price is not None:
            gross_return = price / entry_price - 1
            net_return = gross_return - 2 * fee_rate
            rows.append(
                {
                    "entry_date": entry_date.date().isoformat(),
                    "exit_date": date.date().isoformat(),
                    "entry_price": entry_price,
                    "exit_price": price,
                    "holding_days": int((date - entry_date).days),
                    "gross_return": gross_return,
                    "net_return": net_return,
                }
            )
            entry_date = None
            entry_price = None

    if entry_date is not None and entry_price is not None:
        last_date = close.index[-1]
        last_price = float(close.iloc[-1])
        rows.append(
            {
                "entry_date": entry_date.date().isoformat(),
                "exit_date": "",
                "entry_price": entry_price,
                "exit_price": last_price,
                "holding_days": int((last_date - entry_date).days),
                "gross_return": last_price / entry_price - 1,
                "net_return": last_price / entry_price - 1 - fee_rate,
            }
        )

    return pd.DataFrame(rows)


def calculate_metrics(
    raw_returns: pd.Series,
    net_returns: pd.Series,
    equity: pd.Series,
    position: pd.Series,
    turnover: pd.Series,
    trades: pd.DataFrame,
    initial_capital: float,
    fee_bps: float,
) -> dict[str, float | int | str]:
    total_return = equity.iloc[-1] / initial_capital - 1
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    annual_return = (1 + total_return) ** (1 / years) - 1
    annual_volatility = net_returns.std() * math.sqrt(TRADING_DAYS)
    sharpe = annual_return / annual_volatility if annual_volatility > 0 else np.nan
    drawdown = equity / equity.cummax() - 1
    max_drawdown = drawdown.min()
    exposure = position.mean()
    benchmark_return = (1 + raw_returns).prod() - 1
    avg_turnover = turnover.mean()
    total_fee_drag = turnover.sum() * (fee_bps / 10000)
    trade_count = len(trades)
    win_rate = float((trades["net_return"] > 0).mean()) if trade_count else np.nan
    avg_trade_return = float(trades["net_return"].mean()) if trade_count else np.nan

    return {
        "start_date": equity.index[0].date().isoformat(),
        "end_date": equity.index[-1].date().isoformat(),
        "bars": int(len(equity)),
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_volatility),
        "sharpe": float(sharpe) if not np.isnan(sharpe) else "nan",
        "max_drawdown": float(max_drawdown),
        "benchmark_buy_hold_return": float(benchmark_return),
        "exposure": float(exposure),
        "trade_count": int(trade_count),
        "win_rate": win_rate,
        "avg_trade_return": avg_trade_return,
        "avg_daily_turnover": float(avg_turnover),
        "estimated_fee_drag": float(total_fee_drag),
    }


def pct(value: float | int | str) -> str:
    if isinstance(value, str) or pd.isna(value):
        return "N/A"
    return f"{value * 100:.2f}%"


def num(value: float | int | str) -> str:
    if isinstance(value, str) or pd.isna(value):
        return "N/A"
    return f"{value:.3f}"


def risk_checks(metrics: dict[str, float | int | str]) -> list[str]:
    risks: list[str] = []
    bars = int(metrics["bars"])
    max_drawdown = float(metrics["max_drawdown"])
    trade_count = int(metrics["trade_count"])
    annual_volatility = float(metrics["annual_volatility"])
    avg_daily_turnover = float(metrics["avg_daily_turnover"])
    sharpe_value = metrics["sharpe"]
    sharpe = float(sharpe_value) if not isinstance(sharpe_value, str) else np.nan

    if bars < 500:
        risks.append("样本少于 500 个交易日，结论容易受行情阶段影响。")
    if max_drawdown < -0.2:
        risks.append("最大回撤超过 20%，需要明确仓位上限和止损规则。")
    if trade_count < 5:
        risks.append("交易次数少于 5 次，胜率和单笔收益统计不稳定。")
    if annual_volatility > 0.35:
        risks.append("年化波动率高于 35%，净值曲线可能难以承受。")
    if avg_daily_turnover > 0.08:
        risks.append("平均换手偏高，实盘中滑点和冲击成本可能显著侵蚀收益。")
    if not np.isnan(sharpe) and sharpe < 0.8:
        risks.append("Sharpe 低于 0.8，风险调整后收益偏弱。")
    if not risks:
        risks.append("未触发内置高风险阈值，但仍需做样本外、参数扰动和不同市场阶段验证。")
    return risks


def write_report(
    output_path: Path,
    symbol: str,
    adjust: str,
    fast: int,
    slow: int,
    fee_bps: float,
    data: pd.DataFrame,
    result: BacktestResult,
    artifact_names: dict[str, str],
) -> None:
    latest = data.iloc[-1]
    metrics = result.metrics
    risks = risk_checks(metrics)

    lines = [
        f"# A股研究报告: {symbol}",
        "",
        "## 数据",
        "",
        f"- 数据源: AKShare `stock_zh_a_hist`",
        f"- 区间: {metrics['start_date']} 至 {metrics['end_date']}",
        f"- 复权: `{adjust or 'none'}`",
        f"- 样本数: {metrics['bars']} 个交易日",
        "",
        "## 最新技术状态",
        "",
        f"- 收盘价: {latest['close']:.2f}",
        f"- SMA{fast}: {latest.get(f'sma_{fast}', np.nan):.2f}",
        f"- SMA{slow}: {latest.get(f'sma_{slow}', np.nan):.2f}",
        f"- RSI14: {latest.get('rsi_14', np.nan):.2f}",
        f"- MACD: {latest.get('macd', np.nan):.3f}, Signal: {latest.get('macd_signal', np.nan):.3f}, Hist: {latest.get('macd_hist', np.nan):.3f}",
        f"- Bollinger: lower {latest.get('boll_lower', np.nan):.2f}, mid {latest.get('boll_mid', np.nan):.2f}, upper {latest.get('boll_upper', np.nan):.2f}",
        f"- ATR14: {latest.get('atr_14', np.nan):.2f}",
        f"- 当前价格回撤: {pct(latest.get('drawdown', np.nan))}",
        "",
        "## 回测设定",
        "",
        f"- 策略: 日线 SMA{fast}/SMA{slow} 多头交叉。快线高于慢线时持有，否则空仓。",
        "- 成交假设: 信号在收盘后确认，下一交易日持仓生效。",
        f"- 单边费用: {fee_bps:.2f} bps。",
        "- 限制: 未模拟涨跌停无法成交、停牌、盘口冲击、税费细项和真实撮合。",
        "",
        "## 回测结果",
        "",
        f"- 策略总收益: {pct(metrics['total_return'])}",
        f"- 买入持有收益: {pct(metrics['benchmark_buy_hold_return'])}",
        f"- 年化收益: {pct(metrics['annual_return'])}",
        f"- 年化波动: {pct(metrics['annual_volatility'])}",
        f"- Sharpe: {num(metrics['sharpe'])}",
        f"- 最大回撤: {pct(metrics['max_drawdown'])}",
        f"- 持仓暴露: {pct(metrics['exposure'])}",
        f"- 交易次数: {metrics['trade_count']}",
        f"- 胜率: {pct(metrics['win_rate'])}",
        f"- 平均单笔净收益: {pct(metrics['avg_trade_return'])}",
        f"- 估算费用拖累: {pct(metrics['estimated_fee_drag'])}",
        "",
        "## 风险检查",
        "",
    ]
    lines.extend([f"- {risk}" for risk in risks])
    lines.extend(
        [
            "",
            "## 产物",
            "",
            f"- 原始行情: `{artifact_names['raw']}`",
            f"- 指标数据: `{artifact_names['indicators']}`",
            f"- 交易明细: `{artifact_names['trades']}`",
            "",
            "## 研究员结论",
            "",
            "这份报告只用于研究和工程验证，不构成投资建议。进入实盘前，至少需要补充样本外验证、参数稳定性测试、不同市场阶段对比、滑点/涨跌停/停牌建模，以及组合层面的仓位和回撤约束。",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.fast >= args.slow:
        raise ValueError("--fast should be smaller than --slow for the default crossover strategy.")

    symbol = args.symbol.strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir) / f"{symbol}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = fetch_daily_data(symbol, args.start, args.end, args.adjust)
    enriched = calculate_indicators(raw, args.fast, args.slow)
    result = run_ma_backtest(enriched, args.fast, args.slow, args.initial_capital, args.fee_bps)

    raw_name = f"{symbol}_raw.csv"
    indicators_name = f"{symbol}_indicators.csv"
    trades_name = f"{symbol}_trades.csv"
    report_name = f"{symbol}_report.md"

    raw.to_csv(out_dir / raw_name, encoding="utf-8-sig")
    enriched.to_csv(out_dir / indicators_name, encoding="utf-8-sig")
    result.trades.to_csv(out_dir / trades_name, index=False, encoding="utf-8-sig")
    pd.DataFrame({"equity": result.equity, "position": result.position, "net_return": result.net_returns}).to_csv(
        out_dir / f"{symbol}_equity.csv",
        encoding="utf-8-sig",
    )

    write_report(
        output_path=out_dir / report_name,
        symbol=symbol,
        adjust=args.adjust,
        fast=args.fast,
        slow=args.slow,
        fee_bps=args.fee_bps,
        data=enriched,
        result=result,
        artifact_names={"raw": raw_name, "indicators": indicators_name, "trades": trades_name},
    )

    print(f"Report written: {out_dir / report_name}")


if __name__ == "__main__":
    main()
