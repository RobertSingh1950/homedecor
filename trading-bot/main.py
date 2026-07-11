#!/usr/bin/env python3
"""Minimal-budget crypto trading bot CLI.

Examples:
  # Backtest all 3 strategies on 1000 hours of real BTC data, $100 budget
  python main.py backtest --symbol BTCUSDT --cash 100

  # Backtest one strategy on synthetic data (works offline)
  python main.py backtest --strategy momentum --offline

  # Paper-trade live prices with fake money (safe — no keys, no funds)
  python main.py paper --symbol BTCUSDT --strategy grid --cash 100
"""

import argparse
import sys

from trading_bot.backtest import run_backtest
from trading_bot.data import fetch_klines, synthetic_candles
from trading_bot.paper import run_paper
from trading_bot.risk import RiskManager
from trading_bot.strategies import make_strategy

ALL_STRATEGIES = ["dca", "grid", "momentum"]


def build_risk(args) -> RiskManager:
    return RiskManager(risk_per_trade=args.risk_per_trade,
                       stop_loss_pct=args.stop_loss,
                       take_profit_pct=args.take_profit,
                       max_drawdown_pct=args.max_drawdown)


def cmd_backtest(args) -> None:
    if args.offline:
        candles = synthetic_candles(n=2000)
        print("Using synthetic data (offline mode) — results are illustrative only.\n")
    else:
        print(f"Fetching {args.limit} x {args.interval} candles for {args.symbol}…\n")
        try:
            candles = fetch_klines(args.symbol, args.interval, args.limit)
        except Exception as exc:
            print(f"Could not reach Binance ({exc}).\n"
                  f"Check your connection, or re-run with --offline for synthetic data.")
            sys.exit(1)

    names = [args.strategy] if args.strategy else ALL_STRATEGIES
    for name in names:
        result = run_backtest(make_strategy(name), candles,
                              start_cash=args.cash, risk=build_risk(args))
        print(result.report())
        print("-" * 50)
    print("Reminder: past performance does not predict future results.")


def cmd_paper(args) -> None:
    run_paper(make_strategy(args.strategy or "momentum"), symbol=args.symbol,
              start_cash=args.cash, poll_seconds=args.poll,
              risk=build_risk(args), max_iterations=args.iterations)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", default="BTCUSDT")
    common.add_argument("--cash", type=float, default=100.0, help="starting budget in USDT")
    common.add_argument("--strategy", choices=ALL_STRATEGIES, default=None)
    common.add_argument("--risk-per-trade", type=float, default=0.02)
    common.add_argument("--stop-loss", type=float, default=0.05)
    common.add_argument("--take-profit", type=float, default=0.10)
    common.add_argument("--max-drawdown", type=float, default=0.20)

    bt = sub.add_parser("backtest", parents=[common], help="test strategies on history")
    bt.add_argument("--interval", default="1h")
    bt.add_argument("--limit", type=int, default=1000)
    bt.add_argument("--offline", action="store_true", help="use synthetic data (no network)")
    bt.set_defaults(func=cmd_backtest)

    pt = sub.add_parser("paper", parents=[common], help="live prices, fake money")
    pt.add_argument("--poll", type=int, default=60, help="seconds between price checks")
    pt.add_argument("--iterations", type=int, default=None, help="stop after N polls (default: run forever)")
    pt.set_defaults(func=cmd_paper)

    args = p.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
