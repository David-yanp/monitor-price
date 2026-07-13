import unittest
from unittest.mock import AsyncMock, patch

from app.models import C2CPrice
from app.prices.errors import PriceProviderError
from app.prices.service import PriceService


class PriceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = PriceService(
            timeout_seconds=2,
            p2p_sample_size=5,
            min_cny_trade_amount=3000,
        )

    async def asyncTearDown(self) -> None:
        await self.service.close()

    async def test_partial_c2c_failure_keeps_other_price_and_status(self) -> None:
        with (
            patch(
                "app.prices.service.fetch_binance_c2c_price",
                new=AsyncMock(side_effect=PriceProviderError("rate limited", http_status=429)),
            ),
            patch(
                "app.prices.service.fetch_okx_c2c_price",
                new=AsyncMock(return_value=(C2CPrice("okx", 6.73), 200)),
            ),
            patch(
                "app.prices.service.fetch_google_usd_cny_rate",
                new=AsyncMock(return_value=(6.79, 200)),
            ),
        ):
            result = await self.service.fetch_result()

        self.assertIsNotNone(result.snapshot)
        self.assertEqual(tuple(quote.source for quote in result.snapshot.quotes), ("okx",))
        statuses = {status.provider: status for status in result.statuses}
        self.assertFalse(statuses["binance"].success)
        self.assertEqual(statuses["binance"].http_status, 429)
        self.assertEqual(statuses["binance"].retry_count, 1)
        self.assertTrue(statuses["okx"].success)
        self.assertTrue(statuses["google"].success)

    async def test_provider_success_after_retry_records_retry_count(self) -> None:
        binance = AsyncMock(
            side_effect=[
                PriceProviderError("temporary failure", http_status=503),
                (C2CPrice("binance", 6.74), 200),
            ]
        )
        with (
            patch("app.prices.service.fetch_binance_c2c_price", new=binance),
            patch(
                "app.prices.service.fetch_okx_c2c_price",
                new=AsyncMock(return_value=(C2CPrice("okx", 6.73), 200)),
            ),
            patch(
                "app.prices.service.fetch_google_usd_cny_rate",
                new=AsyncMock(return_value=(6.79, 200)),
            ),
        ):
            result = await self.service.fetch_result()

        status = next(status for status in result.statuses if status.provider == "binance")
        self.assertTrue(status.success)
        self.assertEqual(status.http_status, 200)
        self.assertEqual(status.retry_count, 1)
        self.assertEqual(binance.await_count, 2)

    async def test_google_failure_preserves_c2c_statuses(self) -> None:
        with (
            patch(
                "app.prices.service.fetch_binance_c2c_price",
                new=AsyncMock(return_value=(C2CPrice("binance", 6.74), 200)),
            ),
            patch(
                "app.prices.service.fetch_okx_c2c_price",
                new=AsyncMock(return_value=(C2CPrice("okx", 6.73), 200)),
            ),
            patch(
                "app.prices.service.fetch_google_usd_cny_rate",
                new=AsyncMock(side_effect=PriceProviderError("parse failed", http_status=200)),
            ),
        ):
            result = await self.service.fetch_result()

        self.assertIsNone(result.snapshot)
        statuses = {status.provider: status for status in result.statuses}
        self.assertTrue(statuses["binance"].success)
        self.assertTrue(statuses["okx"].success)
        self.assertFalse(statuses["google"].success)
        self.assertEqual(statuses["google"].http_status, 200)
        self.assertEqual(statuses["google"].retry_count, 1)


if __name__ == "__main__":
    unittest.main()
