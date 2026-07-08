from __future__ import annotations

from app.models import PriceSnapshot


def should_alert(snapshot: PriceSnapshot, threshold: float) -> bool:
    return snapshot.diff > threshold


def format_snapshot(snapshot: PriceSnapshot, threshold: float) -> str:
    status = "超过阈值" if should_alert(snapshot, threshold) else "未超过阈值"
    local_time = snapshot.checked_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    return (
        f"当前价格差查询\n"
        f"时间: {local_time}\n"
        f"C2C来源: {snapshot.c2c_source}\n"
        f"C2C CNY/USDT: {snapshot.c2c_price:.4f}\n"
        f"Google USD/CNY: {snapshot.usd_cny_rate:.4f}\n"
        f"绝对价差: {snapshot.diff:.4f}\n"
        f"阈值: {threshold:.4f}\n"
        f"状态: {status}"
    )


def format_alert(snapshot: PriceSnapshot, threshold: float) -> str:
    return "价格偏差预警\n" + format_snapshot(snapshot, threshold)
