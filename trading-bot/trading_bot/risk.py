"""Risk management: position sizing, stop-loss, and a max-drawdown kill switch.

On a small budget, risk control matters more than the strategy itself:
a 50% loss requires a 100% gain just to get back to even.
"""

from dataclasses import dataclass


@dataclass
class RiskManager:
    risk_per_trade: float = 0.02      # risk at most 2% of equity per trade
    stop_loss_pct: float = 0.05       # exit a position 5% below entry
    take_profit_pct: float = 0.10     # bank gains 10% above entry
    max_drawdown_pct: float = 0.20    # stop trading entirely at -20% from peak

    peak_equity: float = 0.0
    entry_price: float | None = None
    halted: bool = False

    def position_size(self, equity: float) -> float:
        """Quote amount to deploy so a stop-loss hit costs ~risk_per_trade of equity."""
        if self.stop_loss_pct <= 0:
            return equity * self.risk_per_trade
        return equity * self.risk_per_trade / self.stop_loss_pct

    def on_entry(self, price: float) -> None:
        self.entry_price = price

    def on_exit(self) -> None:
        self.entry_price = None

    def check_exit(self, price: float) -> str | None:
        """Return 'stop_loss' / 'take_profit' if the open position should close."""
        if self.entry_price is None:
            return None
        if price <= self.entry_price * (1 - self.stop_loss_pct):
            return "stop_loss"
        if price >= self.entry_price * (1 + self.take_profit_pct):
            return "take_profit"
        return None

    def check_drawdown(self, equity: float) -> bool:
        """Update peak equity; returns True (and halts) past max drawdown."""
        self.peak_equity = max(self.peak_equity, equity)
        if self.peak_equity > 0 and equity < self.peak_equity * (1 - self.max_drawdown_pct):
            self.halted = True
        return self.halted
