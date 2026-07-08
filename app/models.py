from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PriceSnapshot:
    checked_at: datetime
    c2c_source: str
    c2c_price: float
    usd_cny_rate: float
    diff: float

    @classmethod
    def create(cls, c2c_source: str, c2c_price: float, usd_cny_rate: float) -> "PriceSnapshot":
        return cls(
            checked_at=datetime.now(timezone.utc),
            c2c_source=c2c_source,
            c2c_price=c2c_price,
            usd_cny_rate=usd_cny_rate,
            diff=abs(c2c_price - usd_cny_rate),
        )


@dataclass(frozen=True)
class C2CPrice:
    source: str
    price: float
