import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from app.config import load_settings
from app.prices.binance import extract_binance_prices
from app.prices.okx import extract_okx_prices


class P2PFilterTests(unittest.TestCase):
    def test_binance_filters_ads_below_min_single_order_amount(self) -> None:
        rows = [
            {"adv": {"price": "6.70", "maxSingleTransAmount": "50"}},
            {"adv": {"price": "6.72", "maxSingleTransAmount": "3000"}},
            {"adv": {"price": "6.74", "maxSingleTransAmount": "10000"}},
            {"adv": {"price": "6.76", "maxSingleTransAmount": "20000"}},
        ]

        prices = extract_binance_prices(rows, sample_size=2, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.72, 6.74])

    def test_binance_returns_no_prices_when_all_ads_are_too_small(self) -> None:
        rows = [
            {"adv": {"price": "6.70", "maxSingleTransAmount": "50"}},
            {"adv": {"price": "6.72", "maxSingleTransAmount": "2999.99"}},
        ]

        prices = extract_binance_prices(rows, sample_size=5, min_cny_trade_amount=3000)

        self.assertEqual(prices, [])

    def test_okx_filters_ads_below_min_single_order_amount(self) -> None:
        items = [
            {"price": "6.70", "quoteMaxAmountPerOrder": "1000.00"},
            {"price": "6.72", "quoteMaxAmountPerOrder": "3000.00"},
            {"price": "6.74", "quoteMaxAmountPerOrder": "10000.00"},
            {"price": "6.76", "quoteMaxAmountPerOrder": "20000.00"},
        ]

        prices = extract_okx_prices(items, sample_size=2, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.72, 6.74])

    def test_okx_returns_no_prices_when_all_ads_are_too_small(self) -> None:
        items = [
            {"price": "6.70", "quoteMaxAmountPerOrder": "1000.00"},
            {"price": "6.72", "quoteMaxAmountPerOrder": "2999.99"},
        ]

        prices = extract_okx_prices(items, sample_size=5, min_cny_trade_amount=3000)

        self.assertEqual(prices, [])

    def test_min_cny_trade_amount_can_be_overridden_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "bot.txt").write_text("token", encoding="utf-8")
            (base_dir / ".env").write_text(
                f"BOT_TOKEN_FILE={base_dir / 'bot.txt'}\n"
                "DATABASE_PATH=prices.db\n"
                "MIN_CNY_TRADE_AMOUNT=5000\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"MONITOR_PRICE_CONFIG_DIR": temp_dir}, clear=True):
                settings = load_settings(base_dir)

        self.assertEqual(settings.min_cny_trade_amount, 5000)


if __name__ == "__main__":
    unittest.main()
