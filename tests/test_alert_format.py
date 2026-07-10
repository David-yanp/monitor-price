from datetime import datetime, timezone
import unittest

from app.alerts import format_alert, format_snapshot
from app.models import ExchangeQuote, PriceSnapshot


class AlertFormatTests(unittest.TestCase):
    def test_format_snapshot_uses_mobile_friendly_lines(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime(2026, 7, 8, 9, 36, 8, tzinfo=timezone.utc),
            usd_cny_rate=6.79,
            quotes=(
                ExchangeQuote(source="binance", price=6.72, diff=0.07),
                ExchangeQuote(source="okx", price=6.73, diff=0.06),
            ),
        )

        text = format_snapshot(snapshot, 0.04)

        self.assertIn("当前价格差", text)
        self.assertIn("Google USD/CNY: 6.79", text)
        self.assertIn("<pre>", text)
        self.assertIn("</pre>", text)
        self.assertIn("交易所        C2C      价差  状态", text)
        self.assertIn("BINANCE      6.72    0.07  ALERT", text)
        self.assertIn("OKX          6.73    0.06  ALERT", text)
        self.assertNotIn("```", text)
        self.assertNotIn("超过 +", text)
        self.assertNotIn("------", text)

    def test_format_alert_puts_trigger_summary_first(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime(2026, 7, 8, 9, 36, 8, tzinfo=timezone.utc),
            usd_cny_rate=6.79,
            quotes=(ExchangeQuote(source="binance", price=6.72, diff=0.07),),
        )

        text = format_alert(snapshot, 0.04, snapshot.quotes)

        self.assertTrue(text.startswith("价格偏差预警: BINANCE"))


if __name__ == "__main__":
    unittest.main()
