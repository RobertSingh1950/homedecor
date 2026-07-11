"""Paper broker: simulates fills with exchange-realistic fees and slippage."""

from dataclasses import dataclass, field


@dataclass
class Trade:
    ts: int
    side: str          # "buy" | "sell"
    price: float
    qty: float
    fee: float
    reason: str = ""


@dataclass
class PaperBroker:
    cash: float                     # quote currency (e.g. USDT)
    fee_rate: float = 0.001         # 0.1% taker fee (Binance default)
    slippage: float = 0.0005        # 0.05% adverse slippage per fill
    min_order_quote: float = 5.0    # Binance minimum notional ≈ $5
    position: float = 0.0           # base asset held (e.g. BTC)
    trades: list[Trade] = field(default_factory=list)

    def buy(self, ts: int, price: float, quote_amount: float, reason: str = "") -> Trade | None:
        """Spend up to `quote_amount` of cash on the asset."""
        quote_amount = min(quote_amount, self.cash)
        if quote_amount < self.min_order_quote:
            return None
        fill_price = price * (1 + self.slippage)
        fee = quote_amount * self.fee_rate
        qty = (quote_amount - fee) / fill_price
        self.cash -= quote_amount
        self.position += qty
        trade = Trade(ts, "buy", fill_price, qty, fee, reason)
        self.trades.append(trade)
        return trade

    def sell(self, ts: int, price: float, qty: float | None = None, reason: str = "") -> Trade | None:
        """Sell `qty` of the asset (default: entire position)."""
        qty = self.position if qty is None else min(qty, self.position)
        fill_price = price * (1 - self.slippage)
        gross = qty * fill_price
        if gross < self.min_order_quote:
            return None
        fee = gross * self.fee_rate
        self.cash += gross - fee
        self.position -= qty
        trade = Trade(ts, "sell", fill_price, qty, fee, reason)
        self.trades.append(trade)
        return trade

    def equity(self, price: float) -> float:
        return self.cash + self.position * price
