from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from app.config import Settings
from app.main import PriceMonitorApp
from app.models import ExchangeQuote, PriceSnapshot


class AlertDedupeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = PriceMonitorApp(
            Settings(
                bot_token="token",
                telegram_chat_id=None,
                telegram_admin_user_ids=frozenset(),
                database_path=Path(self.temp_dir.name) / "prices.db",
            )
        )
        await self.app.store.init()

    async def asyncTearDown(self) -> None:
        await self.app.close()
        self.temp_dir.cleanup()

    async def test_changed_alert_quotes_skip_same_diff(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            usd_cny_rate=7.20,
            quotes=(ExchangeQuote(source="binance", price=7.27415, diff=0.07415),),
        )

        first = await self.app.changed_alert_quotes(snapshot)
        await self.app.mark_alerted(first)
        second = await self.app.changed_alert_quotes(snapshot)

        self.assertEqual(tuple(quote.source for quote in first), ("binance",))
        self.assertEqual(second, ())

    async def test_changed_alert_quotes_include_changed_diff(self) -> None:
        await self.app.store.set_setting("last_alert_diff:binance", "0.0742")
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            usd_cny_rate=7.20,
            quotes=(ExchangeQuote(source="binance", price=7.281, diff=0.081),),
        )

        changed = await self.app.changed_alert_quotes(snapshot)

        self.assertEqual(tuple(quote.source for quote in changed), ("binance",))


if __name__ == "__main__":
    unittest.main()
