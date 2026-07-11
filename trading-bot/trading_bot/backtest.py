"""Backtester: run a strategy over historical candles and report honest metrics
(fees and slippage included, buy-and-hold benchmark alongside)."""

import math
from dataclasses import dataclass

from .broker import PaperBroker
from .data import Candle
from .risk import RiskManager
from .strategies import Strategy


@dataclass
class BacktestResult:
    strategy: str
    start_cash: float
    final_equity: float
    return_pct: float
    buy_hold_return_pct: float
    max_drawdown_pct: float
    num_trades: int
    total_fees: float
    win_rate_pct: float | None
    halted_by_risk: bool

    def report(self) -> str:
        beat = self.return_pct - self.buy_hold_return_pct
        lines = [
            f"Strategy:        {self.strategy}",
            f"Start cash:      ${self.start_cash:,.2f}",
            f"Final equity:    ${self.final_equity:,.2f}",
            f"Return:          {self.return_pct:+.2f}%",
            f"Buy & hold:      {self.buy_hold_return_pct:+.2f}%  (strategy {'beat' if beat >= 0 else 'lost to'} it by {abs(beat):.2f}%)",
            f"Max drawdown:    {self.max_drawdown_pct:.2f}%",
            f"Trades:          {self.num_trades}  (fees paid: ${self.total_fees:,.2f})",
        ]
        if self.win_rate_pct is not None:
            lines.append(f"Win rate:        {self.win_rate_pct:.1f}% of closed round-trips")
        if self.halted_by_risk:
            lines.append("NOTE: trading was HALTED by the max-drawdown kill switch.")
        return "\n".join(lines)


def run_backtest(strategy: Strategy, candles: list[Candle], start_cash: float = 100.0,
                 risk: RiskManager | None = None, fee_rate: float = 0.001) -> BacktestResult:
    broker = PaperBroker(cash=start_cash, fee_rate=fee_rate)
    risk = risk or RiskManager()
    closes = [c.close for c in candles]

    peak = start_cash
    max_dd = 0.0
    wins = losses = 0
    entry_cost: float | None = None

    for i, candle in enumerate(candles):
        price = candle.close
        equity = broker.equity(price)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100)

        if risk.check_drawdown(equity):
            if broker.position > 0:
                broker.sell(candle.ts, price, reason="kill_switch")
            break

        # risk exits take priority over strategy signals
        exit_reason = risk.check_exit(price)
        if exit_reason and broker.position > 0:
            trade = broker.sell(candle.ts, price, reason=exit_reason)
            if trade and entry_cost is not None:
                pnl = trade.qty * trade.price - trade.fee - entry_cost
                wins, losses = wins + (pnl > 0), losses + (pnl <= 0)
                entry_cost = None
            risk.on_exit()
            continue

        sig = strategy.signal(i, closes)
        if sig == "buy" and broker.position == 0:
            amount = risk.position_size(equity)
            if broker.buy(candle.ts, price, amount, reason=strategy.name):
                risk.on_entry(price)
                t = broker.trades[-1]
                entry_cost = t.qty * t.price + t.fee
        elif sig == "buy" and strategy.name in ("dca", "grid"):
            # accumulating strategies may add to a position
            amount = risk.position_size(equity)
            broker.buy(candle.ts, price, amount, reason=strategy.name)
        elif sig == "sell" and broker.position > 0:
            qty = None if strategy.name == "momentum" else broker.position / 2
            trade = broker.sell(candle.ts, price, qty, reason=strategy.name)
            if trade and entry_cost is not None and broker.position == 0:
                pnl = trade.qty * trade.price - trade.fee - entry_cost
                wins, losses = wins + (pnl > 0), losses + (pnl <= 0)
                entry_cost = None
                risk.on_exit()

    final_price = closes[-1]
    final_equity = broker.equity(final_price)
    first_valid = next((c for c in closes if not math.isnan(c)), closes[0])
    closed = wins + losses

    return BacktestResult(
        strategy=strategy.name,
        start_cash=start_cash,
        final_equity=final_equity,
        return_pct=(final_equity / start_cash - 1) * 100,
        buy_hold_return_pct=(final_price / first_valid - 1) * 100,
        max_drawdown_pct=max_dd,
        num_trades=len(broker.trades),
        total_fees=sum(t.fee for t in broker.trades),
        win_rate_pct=(wins / closed * 100) if closed else None,
        halted_by_risk=risk.halted,
    )
