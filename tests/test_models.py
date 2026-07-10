import unittest

from app.models import C2CPrice, PriceSnapshot


class PriceSnapshotTests(unittest.TestCase):
    def test_create_rounds_prices_and_diff_to_two_decimals(self) -> None:
        snapshot = PriceSnapshot.create(
            (
                C2CPrice(source="binance", price=6.735),
                C2CPrice(source="okx", price=6.744),
            ),
            usd_cny_rate=6.79285066,
        )

        self.assertEqual(snapshot.usd_cny_rate, 6.79)
        self.assertEqual(snapshot.quotes[0].price, 6.74)
        self.assertEqual(snapshot.quotes[0].diff, 0.05)
        self.assertEqual(snapshot.quotes[1].price, 6.74)
        self.assertEqual(snapshot.quotes[1].diff, 0.05)


if __name__ == "__main__":
    unittest.main()
