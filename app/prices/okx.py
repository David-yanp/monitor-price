from __future__ import annotations

from statistics import median

import aiohttp

from app.models import C2CPrice


OKX_P2P_URL = "https://www.okx.com/v3/c2c/tradingOrders/books"


async def fetch_okx_c2c_price(
    session: aiohttp.ClientSession,
    sample_size: int,
    min_cny_trade_amount: float,
) -> C2CPrice:
    params = {
        "quoteCurrency": "CNY",
        "baseCurrency": "USDT",
        "side": "sell",
        "paymentMethod": "all",
        "userType": "all",
        "showTrade": "false",
        "showFollow": "false",
        "showAlreadyTraded": "false",
        "isAbleFilter": "false",
        "urlId": "1",
    }
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"}

    async with session.get(OKX_P2P_URL, params=params, headers=headers) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)

    raw_items = data.get("data")
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("sell") or raw_items.get("asks") or raw_items.get("items")
    if not isinstance(raw_items, list):
        raise RuntimeError("OKX P2P returned an unexpected response shape.")

    prices = extract_okx_prices(raw_items, sample_size, min_cny_trade_amount)

    if not prices:
        raise RuntimeError(f"OKX P2P returned no USDT/CNY prices meeting min {min_cny_trade_amount:g} CNY single-order amount.")

    return C2CPrice(source="okx", price=float(median(prices)))


def extract_okx_prices(
    raw_items: list[object],
    sample_size: int,
    min_cny_trade_amount: float,
) -> list[float]:
    prices: list[float] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        price = item.get("price") or item.get("quotePrice")
        max_amount = item.get("quoteMaxAmountPerOrder")
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
