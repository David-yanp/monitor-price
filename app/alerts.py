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
    lines = [
        "当前价格差",
        f"时间: {local_time}",
        f"Google USD/CNY: {snapshot.usd_cny_rate:.4f}",
        f"阈值: {threshold:.4f}",
        "",
    ]
    for quote in snapshot.quotes:
        status = "超过" if quote.diff > threshold else "正常"
        overage = max(quote.diff - threshold, 0)
        lines.append(
            f"{quote.source.upper()}: {quote.price:.4f} | 差 {quote.diff:.4f} | {status}"
            f"{f' +{overage:.4f}' if overage else ''}"
        )
    return "\n".join(lines)


def format_alert(
    snapshot: PriceSnapshot,
    threshold: float,
    changed_quotes: Iterable[ExchangeQuote],
) -> str:
    changed_sources = ", ".join(quote.source.upper() for quote in changed_quotes)
    return f"价格偏差预警: {changed_sources}\n\n" + format_snapshot(snapshot, threshold)
