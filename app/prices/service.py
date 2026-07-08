from __future__ import annotations

import asyncio

import aiohttp

from app.models import C2CPrice, PriceSnapshot
from app.prices.binance import fetch_binance_c2c_price
from app.prices.google import fetch_google_usd_cny_rate
from app.prices.okx import fetch_okx_c2c_price


class PriceService:
    def __init__(self, timeout_seconds: float, p2p_sample_size: int) -> None:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._timeout_seconds = timeout_seconds
        self._p2p_sample_size = p2p_sample_size

    async def close(self) -> None:
        await self._session.close()

    async def fetch_snapshot(self) -> PriceSnapshot:
        c2c_price = await self._fetch_c2c_with_fallback()
        usd_cny_rate = await asyncio.wait_for(
            fetch_google_usd_cny_rate(self._session),
            timeout=self._timeout_seconds,
        )
        return PriceSnapshot.create(c2c_price.source, c2c_price.price, usd_cny_rate)

    async def _fetch_c2c_with_fallback(self) -> C2CPrice:
        errors: list[str] = []
        for provider in (fetch_binance_c2c_price, fetch_okx_c2c_price):
            try:
                return await asyncio.wait_for(
                    provider(self._session, self._p2p_sample_size),
                    timeout=self._timeout_seconds,
                )
            except Exception as exc:
                errors.append(f"{provider.__name__}: {exc}")
        raise RuntimeError("; ".join(errors))
