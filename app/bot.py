from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

import aiohttp


logger = logging.getLogger(__name__)

CommandHandler = Callable[[int, int | None, str], Awaitable[str]]

BOT_COMMANDS = (
    {"command": "start", "description": "列出当前支持的命令"},
    {"command": "commands", "description": "列出当前支持的命令"},
    {"command": "query", "description": "实时查询当前价格差"},
    {"command": "chatid", "description": "显示当前 chat_id 和 user_id"},
    {"command": "setalert", "description": "将当前会话设为预警接收目标"},
    {"command": "notifytime", "description": "设置每日通知时间段"},
    {"command": "interval", "description": "设置检查频率"},
    {"command": "settings", "description": "查看通知配置"},
    {"command": "status", "description": "查看预警目标配置"},
)


class TelegramBot:
    def __init__(self, bot_token: str, command_handler: CommandHandler) -> None:
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.command_handler = command_handler
        self._offset = 0

    async def send_message(self, chat_id: str | int, text: str) -> None:
        async with aiohttp.ClientSession() as session:
            await self._send_message(session, chat_id, text)

    async def sync_commands(self) -> None:
        async with aiohttp.ClientSession() as session:
            await self._delete_commands(session)
            await self._set_commands(session)
        logger.info("Telegram bot commands synced.")

    async def run_polling(self) -> None:
        logger.info("Telegram bot polling started.")
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    updates = await self._get_updates(session)
                    for update in updates:
                        await self._handle_update(session, update)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Telegram polling failed; retrying soon.")
                    await asyncio.sleep(5)

    async def _get_updates(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        params = {"timeout": 30, "offset": self._offset}
        async with session.get(f"{self.base_url}/getUpdates", params=params) as response:
            response.raise_for_status()
            payload = await response.json()

        if not payload.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {payload}")
        return payload.get("result") or []

    async def _delete_commands(self, session: aiohttp.ClientSession) -> None:
        async with session.post(f"{self.base_url}/deleteMyCommands", json={}) as response:
            response.raise_for_status()
            data = await response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram deleteMyCommands failed: {data}")

    async def _set_commands(self, session: aiohttp.ClientSession) -> None:
        payload = {"commands": list(BOT_COMMANDS)}
        async with session.post(f"{self.base_url}/setMyCommands", json=payload) as response:
            response.raise_for_status()
            data = await response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram setMyCommands failed: {data}")

    async def _handle_update(self, session: aiohttp.ClientSession, update: dict[str, Any]) -> None:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            self._offset = max(self._offset, update_id + 1)

        message = update.get("message") or update.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not text or chat_id is None:
            return

        user = message.get("from") or {}
        user_id = user.get("id")
        reply = await self.command_handler(
            int(chat_id),
            int(user_id) if isinstance(user_id, int) else None,
            text,
        )
        await self._send_message(session, chat_id, reply)

    async def _send_message(
        self,
        session: aiohttp.ClientSession,
        chat_id: str | int,
        text: str,
    ) -> None:
        payload = {"chat_id": chat_id, "text": text}
        payload["parse_mode"] = "HTML"
        async with session.post(f"{self.base_url}/sendMessage", json=payload) as response:
            response.raise_for_status()
            data = await response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {data}")
