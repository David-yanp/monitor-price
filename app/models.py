from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


PRICE_DECIMAL_PLACES = 2


@dataclass(frozen=True)
class ExchangeQuote:
    source: str
    price: float
    diff: float
    error: str | None = None


@dataclass(frozen=True)
class PriceSnapshot:
    checked_at: datetime
    usd_cny_rate: float
    quotes: tuple[ExchangeQuote, ...]

    @classmethod
    def create(cls, c2c_prices: tuple["C2CPrice", ...], usd_cny_rate: float) -> "PriceSnapshot":
        rounded_usd_cny_rate = round(usd_cny_rate, PRICE_DECIMAL_PLACES)
        return cls(
            checked_at=datetime.now(timezone.utc),
            usd_cny_rate=rounded_usd_cny_rate,
            quotes=tuple(
                ExchangeQuote(
                    source=c2c_price.source,
                    price=round(c2c_price.price, PRICE_DECIMAL_PLACES),
                    diff=round(
                        abs(round(c2c_price.price, PRICE_DECIMAL_PLACES) - rounded_usd_cny_rate),
                        PRICE_DECIMAL_PLACES,
                    ),
                )
                for c2c_price in c2c_prices
            ),
        )

    @property
    def c2c_source(self) -> str:
        return self.primary_quote.source

    @property
    def c2c_price(self) -> float:
        return self.primary_quote.price

    @property
    def diff(self) -> float:
        return self.primary_quote.diff

    @property
    def primary_quote(self) -> ExchangeQuote:
        return max(self.quotes, key=lambda quote: quote.diff)


@dataclass(frozen=True)
class C2CPrice:
    source: str
    price: float
