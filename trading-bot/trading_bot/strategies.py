"""Three strategies suited to small budgets.

Each strategy sees one candle at a time and returns a signal:
  "buy", "sell", or None (hold). The backtester/paper-trader handles
  sizing, fees, and risk overrides (stop-loss / take-profit / kill switch).

- DCA: buy a fixed amount every N candles. Hardest to beat for beginners;
  never sells, so 'profit' is unrealized until you withdraw.
- Grid: buy dips / sell rips inside a range. Earns in sideways markets,
  loses in strong trends. Good fee-aware spacing matters.
- Momentum: SMA crossover with an RSI filter. Trend-following; few trades,
  which keeps fees low — important when the budget is small.
"""

from dataclasses import dataclass, field

from .indicators import rsi, sma


class Strategy:
    name = "base"

    def signal(self, i: int, closes: list[float]) -> str | None:
        raise NotImplementedError


@dataclass
class DCAStrategy(Strategy):
    name = "dca"
    every_n_candles: int = 24  # once a day on 1h candles

    def signal(self, i: int, closes: list[float]) -> str | None:
        return "buy" if i % self.every_n_candles == 0 else None


@dataclass
class GridStrategy(Strategy):
    """Rebuilds a symmetric grid around the first price seen; buys when price
    falls a grid step below the last fill, sells when it rises a step above."""
    name = "grid"
    step_pct: float = 0.015          # 1.5% between grid levels (> 2x round-trip fees)
    last_fill: float | None = None

    def signal(self, i: int, closes: list[float]) -> str | None:
        price = closes[i]
        if self.last_fill is None:
            self.last_fill = price
            return None
        if price <= self.last_fill * (1 - self.step_pct):
            self.last_fill = price
            return "buy"
        if price >= self.last_fill * (1 + self.step_pct):
            self.last_fill = price
            return "sell"
        return None


@dataclass
class MomentumStrategy(Strategy):
    """Buy when fast SMA crosses above slow SMA and RSI isn't overbought;
    sell on the opposite cross."""
    name = "momentum"
    fast: int = 20
    slow: int = 50
    rsi_period: int = 14
    rsi_max_entry: float = 70.0
    _cache: dict = field(default_factory=dict, repr=False)

    def _lines(self, closes: list[float]):
        key = (id(closes), len(closes))
        if key not in self._cache:
            self._cache.clear()
            self._cache[key] = (sma(closes, self.fast), sma(closes, self.slow),
                                rsi(closes, self.rsi_period))
        return self._cache[key]

    def signal(self, i: int, closes: list[float]) -> str | None:
        fast_line, slow_line, rsi_line = self._lines(closes)
        if i < 1 or None in (fast_line[i], slow_line[i], fast_line[i - 1],
                             slow_line[i - 1], rsi_line[i]):
            return None
        crossed_up = fast_line[i - 1] <= slow_line[i - 1] and fast_line[i] > slow_line[i]
        crossed_down = fast_line[i - 1] >= slow_line[i - 1] and fast_line[i] < slow_line[i]
        if crossed_up and rsi_line[i] < self.rsi_max_entry:
            return "buy"
        if crossed_down:
            return "sell"
        return None


def make_strategy(name: str, params: dict | None = None) -> Strategy:
    params = params or {}
    registry = {"dca": DCAStrategy, "grid": GridStrategy, "momentum": MomentumStrategy}
    if name not in registry:
        raise ValueError(f"unknown strategy '{name}' (choose from {sorted(registry)})")
    return registry[name](**params)
