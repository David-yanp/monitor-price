from datetime import datetime, timezone
import unittest

from app.alerts import alertable_quotes, diff_key, should_alert
from app.models import ExchangeQuote, PriceSnapshot


class AlertTests(unittest.TestCase):
    def test_should_alert_uses_absolute_diff(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            usd_cny_rate=7.20,
            quotes=(ExchangeQuote(source="binance", price=7.25, diff=0.05),),
        )

        self.assertIs(should_alert(snapshot, 0.04), True)
        self.assertEqual(tuple(quote.source for quote in alertable_quotes(snapshot, 0.04)), ("binance",))

    def test_should_not_alert_at_threshold(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            usd_cny_rate=7.20,
            quotes=(ExchangeQuote(source="binance", price=7.24, diff=0.04),),
        )

        self.assertIs(should_alert(snapshot, 0.04), False)

    def test_diff_key_uses_display_precision(self) -> None:
        self.assertEqual(diff_key(0.074152139), "0.0742")


if __name__ == "__main__":
    unittest.main()
