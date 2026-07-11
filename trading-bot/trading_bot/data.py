"""Market data: Binance public API (no key needed) + offline synthetic data."""

import csv
import json
import math
import random
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/price"


@dataclass
class Candle:
    ts: int        # open time, ms since epoch
    open: float
    high: float
    low: float
    close: float
    volume: float


def _http_get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={"User-Agent": "mini-trading-bot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 1000) -> list[Candle]:
    """Fetch up to 1000 recent candles from Binance public API."""
    url = f"{BINANCE_KLINES}?symbol={symbol}&interval={interval}&limit={min(limit, 1000)}"
    raw = _http_get_json(url)
    return [
        Candle(ts=int(k[0]), open=float(k[1]), high=float(k[2]),
               low=float(k[3]), close=float(k[4]), volume=float(k[5]))
        for k in raw
    ]


def fetch_price(symbol: str = "BTCUSDT") -> float:
    """Current spot price from Binance public API."""
    data = _http_get_json(f"{BINANCE_TICKER}?symbol={symbol}")
    return float(data["price"])


def save_candles_csv(candles: list[Candle], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "volume"])
        for c in candles:
            w.writerow([c.ts, c.open, c.high, c.low, c.close, c.volume])


def load_candles_csv(path: str | Path) -> list[Candle]:
    with open(path, newline="") as f:
        return [
            Candle(ts=int(r["ts"]), open=float(r["open"]), high=float(r["high"]),
                   low=float(r["low"]), close=float(r["close"]), volume=float(r["volume"]))
            for r in csv.DictReader(f)
        ]


def synthetic_candles(n: int = 2000, start_price: float = 100.0, seed: int = 42,
                      drift: float = 0.00005, vol: float = 0.01) -> list[Candle]:
    """Geometric-random-walk candles for offline testing (no network)."""
    rng = random.Random(seed)
    candles = []
    price = start_price
    ts = int(time.time() * 1000) - n * 3_600_000
    for i in range(n):
        ret = drift + vol * rng.gauss(0, 1) + 0.003 * math.sin(i / 50)
        close = max(price * math.exp(ret), 0.01)
        high = max(price, close) * (1 + abs(rng.gauss(0, vol / 3)))
        low = min(price, close) * (1 - abs(rng.gauss(0, vol / 3)))
        candles.append(Candle(ts=ts + i * 3_600_000, open=price, high=high,
                              low=low, close=close, volume=rng.uniform(10, 1000)))
        price = close
    return candles
