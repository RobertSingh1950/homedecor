# Minimal-Budget Crypto Trading Bot

A small, dependency-free Python bot for learning algorithmic trading safely on a
tiny budget. It backtests and **paper-trades** (real prices, fake money) three
strategies against Binance public market data — no account, no API keys, no
funds at risk.

> ## ⚠️ Read this first
> **No trading bot can guarantee profit.** Most retail trading bots lose money
> after fees. This project is for education: it deliberately ships *without*
> real-money order execution. Validate a strategy with weeks of backtesting and
> paper trading before you even consider risking real funds — and never trade
> money you can't afford to lose. This is not financial advice.

## Why crypto instead of Polymarket?

| | Crypto spot | Polymarket |
|---|---|---|
| Minimum order | ~$5 (Binance) | ~$1, but gas/bridging overhead |
| Account needed to develop | **No** (public data) | Yes (wallet + USDC on Polygon) |
| Geo restrictions | Few for data | US users largely blocked |
| Fees on small budgets | 0.1% taker | 0% trading fee, but spread + on-chain costs |
| Bot tooling | Mature | Thin |

Polymarket bots are viable (mostly market-making and arbitrage between related
markets), but they need on-chain wallet plumbing and real capital just to test.
Crypto lets you build, test, and paper-trade with **$0**, which fits the
"minimum budget" goal — spend nothing until a strategy has proven itself.

## Quick start

Requires Python 3.10+. No packages to install — standard library only.

```bash
cd trading-bot

# Backtest all 3 strategies on the last 1000 hours of real BTC data, $100 budget
python3 main.py backtest --symbol BTCUSDT --cash 100

# No internet? Use synthetic data
python3 main.py backtest --offline

# Paper-trade live prices with fake money (Ctrl+C to stop; state saved to JSON)
python3 main.py paper --symbol BTCUSDT --strategy momentum --cash 100 --poll 60
```

Useful flags: `--strategy dca|grid|momentum`, `--interval 15m|1h|4h|1d`,
`--stop-loss 0.05`, `--take-profit 0.10`, `--risk-per-trade 0.02`,
`--max-drawdown 0.20`.

## The three strategies (and when each earns)

1. **DCA (`dca`)** — buys a fixed amount on a schedule. The hardest strategy
   for a beginner to beat. It "profits" only if the asset appreciates over your
   holding period; it never times the market and rarely trades, so fees stay
   near zero. **Best default for a small budget.**
2. **Grid (`grid`)** — buys 1.5% dips, sells 1.5% rips. Earns steadily in
   sideways/choppy markets; bleeds in strong downtrends (it keeps catching
   falling knives). The grid step must exceed round-trip fees (~0.25%) by a
   wide margin or fees eat every profit.
3. **Momentum (`momentum`)** — SMA(20/50) crossover with an RSI filter. Rides
   trends, sits out chop. Few trades → low fees, which matters enormously at
   small size. Whipsaws in ranging markets.

## Reality check: what "profit on minimum budget" looks like

- With **$100** at Binance's 0.1% fee, every round trip costs ~$0.20 plus
  slippage. A strategy that trades hourly will donate your budget to the
  exchange. Low trade frequency is your biggest edge at small size.
- A *good* outcome for a small systematic strategy is a few percent per month
  with drawdowns you can stomach — not doubling your money.
- The built-in risk manager enforces: max 2% of equity risked per trade, 5%
  stop-loss, 10% take-profit, and a **kill switch that halts all trading at
  20% drawdown** from peak equity. Keep those on.
- Backtest results overstate live results (overfitting, changing regimes,
  real slippage). Always compare against the buy-and-hold benchmark the
  backtester prints — if your strategy doesn't beat holding, just hold.

## Going live later (deliberately not included)

When a strategy has beaten buy-and-hold in paper trading for 4+ weeks, real
execution means: create an exchange API key with *trade-only* permission
(never withdrawal), IP-whitelist it, and swap `PaperBroker` for real order
calls (e.g. via the [`ccxt`](https://github.com/ccxt/ccxt) library). Start
with the exchange minimum (~$10–20) and treat it as tuition, not investment.

## Project layout

```
main.py                  CLI (backtest / paper)
trading_bot/data.py      Binance public data + offline synthetic candles
trading_bot/indicators.py SMA, EMA, RSI (pure python)
trading_bot/strategies.py DCA, Grid, Momentum
trading_bot/broker.py    Paper broker (fees + slippage simulated)
trading_bot/risk.py      Position sizing, stops, drawdown kill switch
trading_bot/backtest.py  Backtester with honest metrics
trading_bot/paper.py     Live paper-trading loop (resumable JSON state)
```
