from __future__ import annotations

from collections.abc import Iterable

from app.models import ExchangeQuote
from app.models import PriceSnapshot


def should_alert(snapshot: PriceSnapshot, threshold: float) -> bool:
    return any(quote.diff > threshold for quote in snapshot.quotes)


def alertable_quotes(snapshot: PriceSnapshot, threshold: float) -> tuple[ExchangeQuote, ...]:
    return tuple(quote for quote in snapshot.quotes if quote.diff > threshold)


def diff_key(diff: float) -> str:
    return f"{diff:.4f}"


def format_snapshot(snapshot: PriceSnapshot, threshold: float) -> str:
    local_time = snapshot.checked_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    rows = [
        "交易所   CNY/USDT  价差    状态",
        "------   --------  ------  --------",
    ]
    for quote in snapshot.quotes:
        status = "ALERT" if quote.diff > threshold else "OK"
        rows.append(f"{quote.source:<8} {quote.price:>8.4f}  {quote.diff:>6.4f}  {status}")

    return (
        f"当前价格差查询\n"
        f"时间: {local_time}\n"
        f"Google USD/CNY: {snapshot.usd_cny_rate:.4f}\n"
        f"阈值: {threshold:.4f}\n"
        f"\n" + "\n".join(rows)
    )


def format_alert(
    snapshot: PriceSnapshot,
    threshold: float,
    changed_quotes: Iterable[ExchangeQuote],
) -> str:
    changed_sources = ", ".join(quote.source for quote in changed_quotes)
    return f"价格偏差预警\n触发交易所: {changed_sources}\n" + format_snapshot(snapshot, threshold)
