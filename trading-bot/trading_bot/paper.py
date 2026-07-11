"""Live paper trading: real prices, fake money.

Polls the Binance public ticker on an interval, feeds prices to the strategy,
and simulates fills through the PaperBroker. State is saved to JSON so you can
stop and resume. Run this for a few weeks before even thinking about real funds.
"""

import json
import time
from dataclasses import asdict
from pathlib import Path

from .broker import PaperBroker, Trade
from .data import fetch_price
from .risk import RiskManager
from .strategies import Strategy


def run_paper(strategy: Strategy, symbol: str, start_cash: float,
              poll_seconds: int = 60, state_path: str | Path = "paper_state.json",
              risk: RiskManager | None = None, max_iterations: int | None = None) -> None:
    state_path = Path(state_path)
    broker = PaperBroker(cash=start_cash)
    risk = risk or RiskManager()

    if state_path.exists():
        saved = json.loads(state_path.read_text())
        broker.cash = saved["cash"]
        broker.position = saved["position"]
        broker.trades = [Trade(**t) for t in saved["trades"]]
        risk.entry_price = saved.get("entry_price")
        risk.peak_equity = saved.get("peak_equity", 0.0)
        print(f"Resumed paper session: cash=${broker.cash:.2f} position={broker.position:.8f}")

    closes: list[float] = []
    print(f"Paper trading {symbol} with strategy '{strategy.name}' — Ctrl+C to stop.")
    iteration = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            try:
                price = fetch_price(symbol)
            except Exception as exc:  # network hiccups shouldn't kill the session
                print(f"[warn] price fetch failed: {exc}; retrying in {poll_seconds}s")
                time.sleep(poll_seconds)
                continue

            closes.append(price)
            ts = int(time.time() * 1000)
            equity = broker.equity(price)

            if risk.check_drawdown(equity):
                if broker.position > 0:
                    broker.sell(ts, price, reason="kill_switch")
                print(f"KILL SWITCH: equity ${equity:.2f} breached max drawdown. Halting.")
                break

            exit_reason = risk.check_exit(price)
            if exit_reason and broker.position > 0:
                broker.sell(ts, price, reason=exit_reason)
                risk.on_exit()
                print(f"[{time.strftime('%H:%M:%S')}] {exit_reason} @ ${price:,.2f}")
            else:
                sig = strategy.signal(len(closes) - 1, closes)
                if sig == "buy":
                    if broker.buy(ts, price, risk.position_size(equity), reason=strategy.name):
                        if broker.position > 0 and risk.entry_price is None:
                            risk.on_entry(price)
                        print(f"[{time.strftime('%H:%M:%S')}] BUY  @ ${price:,.2f}")
                elif sig == "sell" and broker.position > 0:
                    if broker.sell(ts, price, reason=strategy.name):
                        if broker.position == 0:
                            risk.on_exit()
                        print(f"[{time.strftime('%H:%M:%S')}] SELL @ ${price:,.2f}")

            state_path.write_text(json.dumps({
                "cash": broker.cash,
                "position": broker.position,
                "entry_price": risk.entry_price,
                "peak_equity": risk.peak_equity,
                "trades": [asdict(t) for t in broker.trades],
            }, indent=2))

            print(f"[{time.strftime('%H:%M:%S')}] {symbol} ${price:,.2f} | "
                  f"equity ${equity:,.2f} | cash ${broker.cash:,.2f} | "
                  f"position {broker.position:.8f}")
            if max_iterations is None or iteration < max_iterations:
                time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\nStopped. State saved to", state_path)
