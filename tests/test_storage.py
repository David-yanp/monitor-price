import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from app.models import PriceSnapshot
from app.storage import PriceStore


class StorageTests(unittest.TestCase):
    def test_store_records_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "prices.db"
            store = PriceStore(db_path)
            snapshot = PriceSnapshot(
                checked_at=datetime.now(timezone.utc),
                c2c_source="binance",
                c2c_price=7.25,
                usd_cny_rate=7.20,
                diff=0.05,
            )

            async def run() -> None:
                await store.init()
                await store.record_success(snapshot, threshold=0.04, alert_sent=True)

            asyncio.run(run())

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT c2c_source, c2c_price, usd_cny_rate, diff, threshold, alert_sent, error FROM price_checks"
                ).fetchone()

            self.assertEqual(row, ("binance", 7.25, 7.20, 0.05, 0.04, 1, None))

    def test_store_records_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "prices.db"
            store = PriceStore(db_path)

            async def run() -> None:
                await store.init()
                await store.record_error(threshold=0.04, error="network failed")

            asyncio.run(run())

            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT threshold, alert_sent, error FROM price_checks").fetchone()

            self.assertEqual(row, (0.04, 0, "network failed"))

    def test_store_persists_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "prices.db"
            store = PriceStore(db_path)

            async def run() -> str | None:
                await store.init()
                await store.set_setting("telegram_alert_chat_id", "123456")
                return await store.get_setting("telegram_alert_chat_id")

            value = asyncio.run(run())

            self.assertEqual(value, "123456")


if __name__ == "__main__":
    unittest.main()
