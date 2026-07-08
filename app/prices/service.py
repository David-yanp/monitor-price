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
        c2c_prices_task = asyncio.create_task(self._fetch_all_c2c_prices())
        usd_cny_task = asyncio.create_task(
            asyncio.wait_for(
                fetch_google_usd_cny_rate(self._session),
                timeout=self._timeout_seconds,
            )
        )
        c2c_prices, usd_cny_rate = await asyncio.gather(c2c_prices_task, usd_cny_task)
        return PriceSnapshot.create(c2c_prices, usd_cny_rate)

    async def _fetch_all_c2c_prices(self) -> tuple[C2CPrice, ...]:
        providers = (fetch_binance_c2c_price, fetch_okx_c2c_price)
        results = await asyncio.gather(
            *(
                asyncio.wait_for(provider(self._session, self._p2p_sample_size), timeout=self._timeout_seconds)
                for provider in providers
            ),
            return_exceptions=True,
        )

        prices: list[C2CPrice] = []
        errors: list[str] = []
        for provider, result in zip(providers, results):
            if isinstance(result, C2CPrice):
                prices.append(result)
            else:
                errors.append(f"{provider.__name__}: {result}")

        if prices:
            return tuple(prices)
        raise RuntimeError("; ".join(errors))
