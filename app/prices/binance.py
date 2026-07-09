from __future__ import annotations

from statistics import median

import aiohttp

from app.models import C2CPrice


BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
BINANCE_ROWS_PER_PAGE = 20
BINANCE_MAX_PAGES = 5


async def fetch_binance_c2c_price(
    session: aiohttp.ClientSession,
    sample_size: int,
    min_cny_trade_amount: float,
) -> C2CPrice:
    headers = {
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }

    prices: list[float] = []
    for page in range(1, BINANCE_MAX_PAGES + 1):
        payload = {
            "page": page,
            "rows": BINANCE_ROWS_PER_PAGE,
            "payTypes": ["ALIPAY"],
            "asset": "USDT",
            "tradeType": "BUY",
            "fiat": "CNY",
            "publisherType": None,
        }
        async with session.post(BINANCE_P2P_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

        rows = data.get("data") or []
        if not rows:
            break
        prices.extend(
            extract_binance_prices(
                rows,
                sample_size - len(prices),
                min_cny_trade_amount,
            )
        )
        if len(prices) >= sample_size:
            break

    if not prices:
        raise RuntimeError(
            f"Binance P2P returned no ALIPAY USDT/CNY prices with min order at least {min_cny_trade_amount:g} CNY without buyer limits."
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
        try:
            if price is None:
                continue
            if not _is_binance_ad_tradable(adv, min_cny_trade_amount):
                continue
            prices.append(float(price))
        except (TypeError, ValueError):
            continue
        if len(prices) >= sample_size:
            break
    return prices


def _is_binance_ad_tradable(adv: dict, cny_amount: float) -> bool:
    min_amount = _to_float(adv.get("minSingleTransAmount"))
    if min_amount is None:
        return False
    if min_amount < cny_amount:
        return False
    if adv.get("isTradable") is False:
        return False
    if adv.get("takerAdditionalKycRequired") not in (None, 0):
        return False
    for field in ("buyerKycLimit", "buyerRegDaysLimit", "buyerBtcPositionLimit"):
        if adv.get(field) not in (None, ""):
            return False
    return _has_binance_pay_type(adv, "ALIPAY")


def _has_binance_pay_type(adv: dict, pay_type: str) -> bool:
    trade_methods = adv.get("tradeMethods")
    if not isinstance(trade_methods, list):
        return False
    for method in trade_methods:
        if isinstance(method, dict) and method.get("payType") == pay_type:
            return True
    return False


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
