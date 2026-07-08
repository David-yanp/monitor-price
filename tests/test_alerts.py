from datetime import datetime, timezone
import unittest

from app.alerts import should_alert
from app.models import PriceSnapshot


class AlertTests(unittest.TestCase):
    def test_should_alert_uses_absolute_diff(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            c2c_source="binance",
            c2c_price=7.25,
            usd_cny_rate=7.20,
            diff=0.05,
        )

        self.assertIs(should_alert(snapshot, 0.04), True)

    def test_should_not_alert_at_threshold(self) -> None:
        snapshot = PriceSnapshot(
            checked_at=datetime.now(timezone.utc),
            c2c_source="binance",
            c2c_price=7.24,
            usd_cny_rate=7.20,
            diff=0.04,
        )

        self.assertIs(should_alert(snapshot, 0.04), False)


if __name__ == "__main__":
    unittest.main()
