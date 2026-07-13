from __future__ import annotations

import re

import aiohttp

from app.prices.errors import PriceProviderError


GOOGLE_FINANCE_URL = "https://www.google.com/finance/quote/USD-CNY"

PRICE_PATTERNS = (
    re.compile(r'data-last-price="([0-9.]+)"'),
    re.compile(r'"price"\s*:\s*"([0-9.]+)"'),
    re.compile(r'class="[^"]*\bYMlKec\b[^"]*\bfxKbKc\b[^"]*"[^>]*>\s*([0-9.]+)\s*<'),
    re.compile(r'"USD / CNY"\s*,\s*3\s*,\s*null\s*,\s*\[\s*([0-9]+(?:\.[0-9]+)?)'),
    re.compile(r'"USD-CNY"[\s\S]{0,300}?\[\s*([0-9]+(?:\.[0-9]+)?)'),
)


async def fetch_google_usd_cny_rate(session: aiohttp.ClientSession) -> tuple[float, int]:
    headers = {
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }
    async with session.get(GOOGLE_FINANCE_URL, headers=headers) as response:
        response.raise_for_status()
        text = await response.text()
        http_status = response.status

    try:
        return parse_google_usd_cny_rate(text), http_status
    except RuntimeError as exc:
        raise PriceProviderError(str(exc), http_status=http_status) from exc


def parse_google_usd_cny_rate(text: str) -> float:
    for pattern in PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))

    raise RuntimeError("Unable to parse Google USD/CNY rate.")
