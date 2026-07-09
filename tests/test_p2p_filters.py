import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from app.config import load_settings
from app.prices.binance import extract_binance_prices
from app.prices.okx import extract_okx_prices


class P2PFilterTests(unittest.TestCase):
    def test_binance_filters_ads_below_min_order_amount(self) -> None:
        rows = [
            {"adv": self.binance_adv("6.70", "10", "999999")},
            {"adv": self.binance_adv("6.72", "2999.99", "999999")},
            {"adv": self.binance_adv("6.74", "3000", "3000")},
            {"adv": self.binance_adv("6.76", "5000", "10000")},
            {"adv": self.binance_adv("6.78", "8000", "1000")},
        ]

        prices = extract_binance_prices(rows, sample_size=3, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.74, 6.76, 6.78])

    def test_binance_filters_ads_with_buyer_limits_or_non_alipay(self) -> None:
        rows = [
            {"adv": self.binance_adv("6.70", "10", "5000", buyerKycLimit=2)},
            {"adv": self.binance_adv("6.71", "10", "5000", buyerRegDaysLimit=30)},
            {"adv": self.binance_adv("6.72", "10", "5000", buyerBtcPositionLimit="1")},
            {"adv": self.binance_adv("6.73", "10", "5000", takerAdditionalKycRequired=1)},
            {"adv": self.binance_adv("6.74", "10", "5000", pay_type="WECHAT")},
            {"adv": self.binance_adv("6.75", "3000", "5000")},
        ]

        prices = extract_binance_prices(rows, sample_size=5, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.75])

    def test_okx_filters_ads_below_min_order_amount(self) -> None:
        items = [
            self.okx_item("6.70", "10", "999999.00"),
            self.okx_item("6.72", "2999.99", "999999.00"),
            self.okx_item("6.74", "3000", "3000.00"),
            self.okx_item("6.76", "5000", "10000.00"),
            self.okx_item("6.78", "8000", "1000.00"),
        ]

        prices = extract_okx_prices(items, sample_size=3, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.74, 6.76, 6.78])

    def test_okx_filters_ads_with_verification_limits_or_non_alipay(self) -> None:
        items = [
            self.okx_item("6.70", "10", "5000", payment_methods=["wxPay"]),
            self.okx_item("6.71", "10", "5000", verificationRequired=True),
            self.okx_item("6.72", "10", "5000", verificationType=1),
            self.okx_item("6.73", "10", "5000", safetyLimit=True),
            self.okx_item("6.74", "10", "5000", black=True),
            self.okx_item("6.75", "10", "5000", alreadyTraded=True),
            self.okx_item("6.76", "3000", "5000"),
        ]

        prices = extract_okx_prices(items, sample_size=5, min_cny_trade_amount=3000)

        self.assertEqual(prices, [6.76])

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

    def binance_adv(
        self,
        price: str,
        min_amount: str,
        max_amount: str,
        pay_type: str = "ALIPAY",
        **overrides,
    ) -> dict:
        adv = {
            "price": price,
            "minSingleTransAmount": min_amount,
            "maxSingleTransAmount": max_amount,
            "tradeMethods": [{"payType": pay_type}],
            "buyerKycLimit": None,
            "buyerRegDaysLimit": None,
            "buyerBtcPositionLimit": None,
            "isTradable": True,
            "takerAdditionalKycRequired": 0,
        }
        adv.update(overrides)
        return adv

    def okx_item(
        self,
        price: str,
        min_amount: str,
        max_amount: str,
        payment_methods: list[str] | None = None,
        **overrides,
    ) -> dict:
        item = {
            "price": price,
            "quoteMinAmountPerOrder": min_amount,
            "quoteMaxAmountPerOrder": max_amount,
            "paymentMethods": payment_methods or ["aliPay"],
            "verificationRequired": False,
            "verificationType": 0,
            "safetyLimit": False,
            "black": False,
            "alreadyTraded": False,
        }
        item.update(overrides)
        return item


if __name__ == "__main__":
    unittest.main()
