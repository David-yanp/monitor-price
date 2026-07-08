from __future__ import annotations

from statistics import median

import aiohttp

from app.models import C2CPrice


BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"


async def fetch_binance_c2c_price(
    session: aiohttp.ClientSession,
    sample_size: int,
) -> C2CPrice:
    payload = {
        "page": 1,
        "rows": max(sample_size, 1),
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

    rows = data.get("data") or []
    prices: list[float] = []
    for row in rows[:sample_size]:
        adv = row.get("adv") or {}
        price = adv.get("price")
        if price is not None:
            prices.append(float(price))

    if not prices:
        raise RuntimeError("Binance P2P returned no usable USDT/CNY prices.")

    return C2CPrice(source="binance", price=float(median(prices)))
