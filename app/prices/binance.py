from __future__ import annotations

from statistics import median

import aiohttp

from app.models import C2CPrice


BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"


async def fetch_binance_c2c_price(
    session: aiohttp.ClientSession,
    sample_size: int,
    min_cny_trade_amount: float,
) -> C2CPrice:
    payload = {
        "page": 1,
        "rows": max(sample_size * 3, sample_size, 10),
        "payTypes": [],
        "asset": "USDT",
        "tradeType": "BUY",
        "fiat": "CNY",
        "publisherType": None,
    }
    headers = {
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }

    async with session.post(BINANCE_P2P_URL, json=payload, headers=headers) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)

    prices = extract_binance_prices(
        data.get("data") or [],
        sample_size,
        min_cny_trade_amount,
    )

    if not prices:
        raise RuntimeError(
            f"Binance P2P returned no USDT/CNY prices meeting min {min_cny_trade_amount:g} CNY single-order amount."
        )

    return C2CPrice(source="binance", price=float(median(prices)))


def extract_binance_prices(
    rows: list[object],
    sample_size: int,
    min_cny_trade_amount: float,
) -> list[float]:
    prices: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        adv = row.get("adv") or {}
        if not isinstance(adv, dict):
            continue
        price = adv.get("price")
        max_amount = adv.get("maxSingleTransAmount")
        try:
            if price is None or max_amount is None:
                continue
            if float(max_amount) < min_cny_trade_amount:
                continue
            prices.append(float(price))
        except (TypeError, ValueError):
            continue
        if len(prices) >= sample_size:
            break
    return prices
