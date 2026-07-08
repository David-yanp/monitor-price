from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
import re


DEFAULT_NOTIFY_WINDOW = "00:00-23:59"
NOTIFY_WINDOW_KEY = "notify_window"
CHECK_INTERVAL_KEY = "check_interval_seconds"


@dataclass(frozen=True)
class NotifyWindow:
    start: time
    end: time

    def contains(self, current: datetime | None = None) -> bool:
        current_time = (current or datetime.now().astimezone()).time()
        current_minutes = _to_minutes(current_time)
        start_minutes = _to_minutes(self.start)
        end_minutes = _to_minutes(self.end)

        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes <= end_minutes
        return current_minutes >= start_minutes or current_minutes <= end_minutes

    def __str__(self) -> str:
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"


def parse_notify_window(raw_value: str) -> NotifyWindow:
    match = re.fullmatch(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})", raw_value.strip())
    if not match:
        raise ValueError("通知时间段格式应为 HH:MM-HH:MM，例如 08:00-23:30")

    start_hour, start_minute, end_hour, end_minute = (int(part) for part in match.groups())
    try:
        return NotifyWindow(
            start=time(hour=start_hour, minute=start_minute),
            end=time(hour=end_hour, minute=end_minute),
        )
    except ValueError as exc:
        raise ValueError("通知时间段无效，小时必须是 00-23，分钟必须是 00-59") from exc


def parse_interval_seconds(raw_value: str) -> int:
    match = re.fullmatch(r"(\d+)([mh])", raw_value.strip().lower())
    if not match:
        raise ValueError("检查频率格式应为数字加单位，例如 5m、30m、1h")

    amount = int(match.group(1))
    if amount <= 0:
        raise ValueError("检查频率必须大于 0")

    multiplier = 60 if match.group(2) == "m" else 3600
    return amount * multiplier


def format_interval(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute
