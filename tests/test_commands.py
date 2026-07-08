import unittest
from pathlib import Path
import tempfile

from app.config import Settings
from app.main import PriceMonitorApp


class CommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = PriceMonitorApp(
            Settings(
                bot_token="token",
                telegram_chat_id=None,
                telegram_admin_user_ids=frozenset(),
                database_path=Path(self.temp_dir.name) / "prices.db",
            )
        )

    async def asyncTearDown(self) -> None:
        await self.app.close()
        self.temp_dir.cleanup()

    async def test_commands_lists_current_commands(self) -> None:
        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/commands")

        self.assertIn("/query - 实时查询当前价格差", reply)
        self.assertIn("/setalert - 将当前会话设为预警接收目标", reply)

    async def test_status_without_alert_chat_suggests_setalert(self) -> None:
        await self.app.store.init()

        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/status")

        self.assertIn("当前预警 chat_id: 未配置", reply)
        self.assertIn("每日通知时间段: 00:00-23:59", reply)
        self.assertIn("检查频率: 30m", reply)
        self.assertIn("/setalert", reply)

    async def test_notifytime_sets_window(self) -> None:
        await self.app.store.init()

        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/notifytime 08:00-23:30")

        self.assertEqual(reply, "已设置每日通知时间段: 08:00-23:30")
        self.assertEqual(await self.app.store.get_setting("notify_window"), "08:00-23:30")

    async def test_interval_sets_seconds(self) -> None:
        await self.app.store.init()

        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/interval 15m")

        self.assertEqual(reply, "已设置检查频率: 15m")
        self.assertEqual(await self.app.store.get_setting("check_interval_seconds"), "900")

    async def test_settings_shows_runtime_config(self) -> None:
        await self.app.store.init()
        await self.app.store.set_setting("notify_window", "08:00-23:30")
        await self.app.store.set_setting("check_interval_seconds", "900")

        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/settings")

        self.assertIn("每日通知时间段: 08:00-23:30", reply)
        self.assertIn("检查频率: 15m", reply)

    async def test_unauthorized_user_cannot_change_notify_settings(self) -> None:
        await self.app.close()
        self.app = PriceMonitorApp(
            Settings(
                bot_token="token",
                telegram_chat_id=None,
                telegram_admin_user_ids=frozenset({999}),
                database_path=Path(self.temp_dir.name) / "prices.db",
            )
        )
        await self.app.store.init()

        reply = await self.app.handle_command(chat_id=123, user_id=456, text="/notifytime 08:00-23:30")

        self.assertIn("没有权限", reply)
        self.assertIsNone(await self.app.store.get_setting("notify_window"))


if __name__ == "__main__":
    unittest.main()
