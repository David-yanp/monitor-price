from __future__ import annotations

import asyncio
import logging

from app.alerts import alertable_quotes, diff_key, format_alert, format_snapshot
from app.bot import BOT_COMMANDS, TelegramBot
from app.config import Settings, load_settings
from app.prices import PriceService
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
        self.price_service = PriceService(settings.http_timeout_seconds, settings.p2p_sample_size)
        self.bot = TelegramBot(settings.bot_token, self.handle_command)

    async def close(self) -> None:
        await self.price_service.close()

    async def handle_command(self, chat_id: int, user_id: int | None, text: str) -> str:
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        if command in {"/start", "/commands"}:
            return self.format_command_list()
        if command == "/chatid":
            return f"当前 chat_id: {chat_id}\n当前 user_id: {user_id or 'unknown'}"
        if command == "/setalert":
            return await self.set_alert_chat(chat_id, user_id)
        if command == "/status":
            alert_chat_id = await self.get_alert_chat_id()
            if alert_chat_id:
                return f"当前预警 chat_id: {alert_chat_id}"
            return "当前预警 chat_id: 未配置\n请在需要接收预警的会话里发送 /setalert。"
        if command != "/query":
            return "未知命令。请发送 /query 查询当前价格差。"

        try:
            snapshot = await self.price_service.fetch_snapshot()
            return format_snapshot(snapshot, self.settings.price_diff_threshold)
        except Exception as exc:
            logger.exception("/query failed for chat_id=%s", chat_id)
            return f"查询失败: {exc}"

    async def set_alert_chat(self, chat_id: int, user_id: int | None) -> str:
        if not self.can_manage_alerts(user_id):
            return "没有权限设置预警目标。请在 TELEGRAM_ADMIN_USER_IDS 中配置你的 Telegram user_id。"

        await self.store.set_setting("telegram_alert_chat_id", str(chat_id))
        return f"已将当前会话设置为预警接收目标。\nchat_id: {chat_id}"

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

    async def run_monitor_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.check_interval_seconds)

    async def run_once(self) -> None:
        alert_sent = False
        try:
            snapshot = await self.price_service.fetch_snapshot()
            changed_quotes = await self.changed_alert_quotes(snapshot)
            if changed_quotes:
                alert_chat_id = await self.get_alert_chat_id()
                if alert_chat_id:
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
