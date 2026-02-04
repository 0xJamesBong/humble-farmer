"""Fetch Binance spot balances and prices via CCXT."""

from __future__ import annotations

from typing import Dict, Tuple

import ccxt


def connect(exchange_id: str = "binance", api_key: str | None = None, secret: str | None = None) -> ccxt.Exchange:
    """Create CCXT exchange instance. Requires api_key/secret for private (balance) calls."""
    klass = getattr(ccxt, exchange_id)
    return klass(
        {
            "apiKey": api_key or "",
            "secret": secret or "",
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
    )


def fetch_balances_and_prices(
    exchange: ccxt.Exchange,
    symbols: list[str],
) -> Tuple[Dict[str, float], Dict[str, float], float]:
    """
    Fetch spot balances and last prices for given symbols (e.g. USDT, SOL, WBTC, WETH).
    Returns:
      - balances: symbol -> amount (free balance)
      - prices_usdt: symbol -> price in USDT (USDT=1.0)
      - total_usdt: portfolio value in USDT
    """
    # CCXT balance keys: USDT, BTC, ETH, SOL (not WBTC/WETH)
    symbol_to_balance_key = {"USDT": "USDT", "SOL": "SOL", "WBTC": "BTC", "WETH": "ETH"}
    balance = exchange.fetch_balance()
    balances = {}
    for s in symbols:
        key = symbol_to_balance_key.get(s, s)
        total = balance.get(key) or {}
        free = total.get("free") if isinstance(total, dict) else 0
        balances[s] = float(free or 0)

    # Fetch tickers for pairs to get prices in USDT
    prices_usdt: Dict[str, float] = {"USDT": 1.0}
    pairs = ["SOL/USDT", "BTC/USDT", "ETH/USDT"]
    try:
        tickers = exchange.fetch_tickers(pairs)
    except Exception:
        tickers = {}
    for pair, data in tickers.items():
        if isinstance(data, dict) and "last" in data:
            if pair == "SOL/USDT":
                prices_usdt["SOL"] = float(data["last"])
            elif pair == "BTC/USDT":
                prices_usdt["WBTC"] = float(data["last"])
            elif pair == "ETH/USDT":
                prices_usdt["WETH"] = float(data["last"])

    total_usdt = sum(balances.get(s, 0) * prices_usdt.get(s, 0) for s in symbols)
    return balances, prices_usdt, total_usdt
