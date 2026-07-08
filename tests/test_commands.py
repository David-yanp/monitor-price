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
        self.assertIn("/setalert", reply)


if __name__ == "__main__":
    unittest.main()
