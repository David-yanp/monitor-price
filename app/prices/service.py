from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

import aiohttp

from app.models import C2CPrice, PriceFetchResult, PriceSnapshot, ProviderFetchStatus
from app.prices.binance import fetch_binance_c2c_price
from app.prices.google import fetch_google_usd_cny_rate
from app.prices.okx import fetch_okx_c2c_price


ProviderOperation = Callable[[], Awaitable[tuple[Any, int]]]


class PriceService:
    def __init__(self, timeout_seconds: float, p2p_sample_size: int, min_cny_trade_amount: float) -> None:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._timeout_seconds = timeout_seconds
        self._p2p_sample_size = p2p_sample_size
        self._min_cny_trade_amount = min_cny_trade_amount
        self._max_attempts = 2

    async def close(self) -> None:
        await self._session.close()

    async def fetch_snapshot(self) -> PriceSnapshot:
        result = await self.fetch_result()
        if result.snapshot is None:
            raise RuntimeError(result.error or "Price fetch failed.")
        return result.snapshot

    async def fetch_result(self) -> PriceFetchResult:
        results = await asyncio.gather(
            self._fetch_with_status(
                "binance",
                lambda: fetch_binance_c2c_price(
                    self._session,
                    self._p2p_sample_size,
                    self._min_cny_trade_amount,
                ),
            ),
            self._fetch_with_status(
                "okx",
                lambda: fetch_okx_c2c_price(
                    self._session,
                    self._p2p_sample_size,
                    self._min_cny_trade_amount,
                ),
            ),
            self._fetch_with_status(
                "google",
                lambda: fetch_google_usd_cny_rate(self._session),
            ),
        )

        values = {provider: value for provider, value, _status in results}
        statuses = tuple(status for _provider, _value, status in results)
        c2c_prices = tuple(
            value
            for provider, value in values.items()
            if provider in {"binance", "okx"} and isinstance(value, C2CPrice)
        )
        usd_cny_rate = values.get("google")

        errors: list[str] = []
        if not c2c_prices:
            errors.append("No C2C provider returned a usable price.")
        if not isinstance(usd_cny_rate, float):
            errors.append("Google USD/CNY rate is unavailable.")
        if errors:
            provider_errors = [f"{status.provider}: {status.error}" for status in statuses if not status.success]
            return PriceFetchResult(
                snapshot=None,
                statuses=statuses,
                error="; ".join(errors + provider_errors),
            )

        return PriceFetchResult(
            snapshot=PriceSnapshot.create(c2c_prices, usd_cny_rate),
            statuses=statuses,
        )

    async def _fetch_with_status(
        self,
        provider: str,
        operation: ProviderOperation,
    ) -> tuple[str, Any | None, ProviderFetchStatus]:
        started_at = perf_counter()
        last_error: Exception | None = None
        last_http_status: int | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                value, http_status = await asyncio.wait_for(operation(), timeout=self._timeout_seconds)
                return (
                    provider,
                    value,
                    ProviderFetchStatus(
                        provider=provider,
                        success=True,
                        http_status=http_status,
                        elapsed_ms=_elapsed_ms(started_at),
                        retry_count=attempt - 1,
                    ),
                )
            except Exception as exc:
                last_error = exc
                last_http_status = _http_status(exc) or last_http_status
                if attempt < self._max_attempts:
                    await asyncio.sleep(0.5)

        return (
            provider,
            None,
            ProviderFetchStatus(
                provider=provider,
                success=False,
                http_status=last_http_status,
                elapsed_ms=_elapsed_ms(started_at),
                retry_count=self._max_attempts - 1,
                error=str(last_error) if last_error else "Unknown provider error.",
            ),
        )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _http_status(exc: Exception) -> int | None:
    status = getattr(exc, "http_status", None)
    if isinstance(status, int):
        return status
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None
