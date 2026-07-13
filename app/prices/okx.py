from __future__ import annotations

from statistics import median

import aiohttp

from app.models import C2CPrice
from app.prices.errors import PriceProviderError


OKX_P2P_URL = "https://www.okx.com/v3/c2c/tradingOrders/books"


async def fetch_okx_c2c_price(
    session: aiohttp.ClientSession,
    sample_size: int,
    min_cny_trade_amount: float,
) -> tuple[C2CPrice, int]:
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
        http_status = response.status

    raw_items = data.get("data")
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("sell") or raw_items.get("asks") or raw_items.get("items")
    if not isinstance(raw_items, list):
        raise PriceProviderError("OKX P2P returned an unexpected response shape.", http_status=http_status)

    prices = extract_okx_prices(raw_items, sample_size, min_cny_trade_amount)

    if not prices:
        raise PriceProviderError(
            f"OKX P2P returned no ALIPAY USDT/CNY prices with min order at least {min_cny_trade_amount:g} CNY without verification limits.",
            http_status=http_status,
        )

    return C2CPrice(source="okx", price=float(median(prices))), http_status


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
        try:
            if price is None:
                continue
            if not _is_okx_ad_tradable(item, min_cny_trade_amount):
                continue
            prices.append(float(price))
        except (TypeError, ValueError):
            continue
        if len(prices) >= sample_size:
            break
    return prices


def _is_okx_ad_tradable(item: dict, cny_amount: float) -> bool:
    min_amount = _to_float(item.get("quoteMinAmountPerOrder"))
    if min_amount is None:
        return False
    if min_amount < cny_amount:
        return False
    if "aliPay" not in (item.get("paymentMethods") or []):
        return False
    if item.get("verificationRequired") not in (False, None):
        return False
    if item.get("verificationType") not in (0, None):
        return False
    if item.get("safetyLimit") not in (False, None):
        return False
    if item.get("black") not in (False, None):
        return False
    if item.get("alreadyTraded") not in (False, None):
        return False
    return True


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
