from __future__ import annotations

import asyncio
from html import escape
import logging

from app.alerts import alertable_quotes, diff_key, format_alert, format_snapshot
from app.bot import BOT_COMMANDS, TelegramBot
from app.config import Settings, load_settings
from app.prices import PriceService
from app.runtime_config import (
    CHECK_INTERVAL_KEY,
    DEFAULT_NOTIFY_WINDOW,
    NOTIFY_WINDOW_KEY,
    format_interval,
    parse_interval_seconds,
    parse_notify_window,
)
from app.storage import PriceStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PriceMonitorApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = PriceStore(settings.database_path)
        self.price_service = PriceService(
            settings.http_timeout_seconds,
            settings.p2p_sample_size,
            settings.min_cny_trade_amount,
        )
        self.bot = TelegramBot(settings.bot_token, self.handle_command)

    async def close(self) -> None:
        await self.price_service.close()

    async def handle_command(self, chat_id: int, user_id: int | None, text: str) -> str:
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        arg_text = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) > 1 else ""
        if command in {"/start", "/commands"}:
            return self.format_command_list()
        if command == "/chatid":
            return f"当前 chat_id: {chat_id}\n当前 user_id: {user_id or 'unknown'}"
        if command == "/setalert":
            return await self.set_alert_chat(chat_id, user_id)
        if command == "/notifytime":
            return await self.set_notify_window(user_id, arg_text)
        if command == "/interval":
            return await self.set_check_interval(user_id, arg_text)
        if command == "/settings":
            return await self.format_settings()
        if command == "/status":
            return await self.format_settings(include_hint=True)
        if command != "/query":
            return "未知命令。请发送 /query 查询当前价格差。"

        try:
            snapshot = await self.price_service.fetch_snapshot()
            return format_snapshot(snapshot, self.settings.price_diff_threshold)
        except Exception as exc:
            logger.exception("/query failed for chat_id=%s", chat_id)
            return f"查询失败: {escape(str(exc))}"

    async def set_alert_chat(self, chat_id: int, user_id: int | None) -> str:
        if not self.can_manage_alerts(user_id):
            return "没有权限设置预警目标。请在 TELEGRAM_ADMIN_USER_IDS 中配置你的 Telegram user_id。"

        await self.store.set_setting("telegram_alert_chat_id", str(chat_id))
        return f"已将当前会话设置为预警接收目标。\nchat_id: {chat_id}"

    async def set_notify_window(self, user_id: int | None, raw_value: str) -> str:
        if not self.can_manage_alerts(user_id):
            return "没有权限设置通知时间段。请在 TELEGRAM_ADMIN_USER_IDS 中配置你的 Telegram user_id。"
        if not raw_value:
            return "用法: /notifytime 08:00-23:30"

        try:
            notify_window = parse_notify_window(raw_value)
        except ValueError as exc:
            return str(exc)

        await self.store.set_setting(NOTIFY_WINDOW_KEY, str(notify_window))
        return f"已设置每日通知时间段: {notify_window}"

    async def set_check_interval(self, user_id: int | None, raw_value: str) -> str:
        if not self.can_manage_alerts(user_id):
            return "没有权限设置检查频率。请在 TELEGRAM_ADMIN_USER_IDS 中配置你的 Telegram user_id。"
        if not raw_value:
            return "用法: /interval 15m"

        try:
            seconds = parse_interval_seconds(raw_value)
        except ValueError as exc:
            return str(exc)

        await self.store.set_setting(CHECK_INTERVAL_KEY, str(seconds))
        return f"已设置检查频率: {format_interval(seconds)}"

    async def format_settings(self, include_hint: bool = False) -> str:
        alert_chat_id = await self.get_alert_chat_id()
        notify_window = await self.get_notify_window()
        interval_seconds = await self.get_check_interval_seconds()

        lines = [
            f"当前预警 chat_id: {alert_chat_id or '未配置'}",
            f"每日通知时间段: {notify_window}",
            f"检查频率: {format_interval(interval_seconds)}",
            f"阈值: {self.settings.price_diff_threshold:.4f}",
        ]
        if include_hint and not alert_chat_id:
            lines.append("请在需要接收预警的会话里发送 /setalert。")
        return "\n".join(lines)

    def format_command_list(self) -> str:
        lines = ["当前支持的命令:"]
        for item in BOT_COMMANDS:
            lines.append(f"/{item['command']} - {item['description']}")
        return "\n".join(lines)

    def can_manage_alerts(self, user_id: int | None) -> bool:
        if not self.settings.telegram_admin_user_ids:
            return True
        return user_id in self.settings.telegram_admin_user_ids

    async def get_alert_chat_id(self) -> str | None:
        if self.settings.telegram_chat_id:
            return self.settings.telegram_chat_id
        return await self.store.get_setting("telegram_alert_chat_id")

    async def get_notify_window(self):
        raw_value = await self.store.get_setting(NOTIFY_WINDOW_KEY)
        try:
            return parse_notify_window(raw_value or DEFAULT_NOTIFY_WINDOW)
        except ValueError:
            return parse_notify_window(DEFAULT_NOTIFY_WINDOW)

    async def get_check_interval_seconds(self) -> int:
        raw_value = await self.store.get_setting(CHECK_INTERVAL_KEY)
        if raw_value is None:
            return self.settings.check_interval_seconds
        try:
            seconds = int(raw_value)
        except ValueError:
            return self.settings.check_interval_seconds
        return seconds if seconds > 0 else self.settings.check_interval_seconds

    async def run_monitor_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(await self.get_check_interval_seconds())

    async def run_once(self) -> None:
        alert_sent = False
        try:
            snapshot = await self.price_service.fetch_snapshot()
            changed_quotes = await self.changed_alert_quotes(snapshot)
            if changed_quotes:
                alert_chat_id = await self.get_alert_chat_id()
                notify_window = await self.get_notify_window()
                if not notify_window.contains():
                    logger.info("Alert threshold exceeded, but current time is outside notify window %s.", notify_window)
                elif alert_chat_id:
                    await self.bot.send_message(
                        alert_chat_id,
                        format_alert(snapshot, self.settings.price_diff_threshold, changed_quotes),
                    )
                    await self.mark_alerted(changed_quotes)
                    alert_sent = True
                else:
                    logger.warning("Alert threshold exceeded, but TELEGRAM_CHAT_ID is not configured.")

            await self.store.record_success(
                snapshot,
                self.settings.price_diff_threshold,
                alert_sent,
            )
            logger.info(
                "Recorded price check: sources=%s usd_cny=%.4f max_diff=%.4f alert=%s",
                ",".join(quote.source for quote in snapshot.quotes),
                snapshot.usd_cny_rate,
                snapshot.diff,
                alert_sent,
            )
        except Exception as exc:
            logger.exception("Price monitor check failed.")
            await self.store.record_error(self.settings.price_diff_threshold, str(exc))

    async def changed_alert_quotes(self, snapshot):
        changed = []
        for quote in alertable_quotes(snapshot, self.settings.price_diff_threshold):
            current_key = diff_key(quote.diff)
            previous_key = await self.store.get_setting(f"last_alert_diff:{quote.source}")
            if previous_key != current_key:
                changed.append(quote)
        return tuple(changed)

    async def mark_alerted(self, quotes) -> None:
        for quote in quotes:
            await self.store.set_setting(f"last_alert_diff:{quote.source}", diff_key(quote.diff))

    async def run(self) -> None:
        await self.store.init()
        await self.bot.sync_commands()
        await asyncio.gather(self.run_monitor_loop(), self.bot.run_polling())


async def async_main() -> None:
    settings = load_settings()
    app = PriceMonitorApp(settings)
    try:
        await app.run()
    finally:
        await app.close()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
