from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_value(dotenv: dict[str, str], key: str, default: str) -> str:
    return os.getenv(key) or dotenv.get(key) or default


@dataclass(frozen=True)
class Settings:
    bot_token: str
    telegram_chat_id: str | None
    telegram_admin_user_ids: frozenset[int]
    database_path: Path
    check_interval_seconds: int = 1800
    price_diff_threshold: float = 0.04
    http_timeout_seconds: float = 12.0
    p2p_sample_size: int = 5


def load_settings(base_dir: Path = BASE_DIR) -> Settings:
    dotenv = _load_dotenv(base_dir / ".env")
    token_path = base_dir / "bot.txt"

    if not token_path.exists():
        raise RuntimeError("Missing bot.txt with Telegram bot token.")

    bot_token = token_path.read_text(encoding="utf-8").strip()
    if not bot_token:
        raise RuntimeError("bot.txt is empty.")

    database_path = Path(_get_value(dotenv, "DATABASE_PATH", "prices.db"))
    if not database_path.is_absolute():
        database_path = base_dir / database_path

    telegram_chat_id = _get_value(dotenv, "TELEGRAM_CHAT_ID", "").strip() or None
    telegram_admin_user_ids = _parse_int_set(_get_value(dotenv, "TELEGRAM_ADMIN_USER_IDS", ""))

    return Settings(
        bot_token=bot_token,
        telegram_chat_id=telegram_chat_id,
        telegram_admin_user_ids=telegram_admin_user_ids,
        database_path=database_path,
        check_interval_seconds=int(_get_value(dotenv, "CHECK_INTERVAL_SECONDS", "1800")),
        price_diff_threshold=float(_get_value(dotenv, "PRICE_DIFF_THRESHOLD", "0.04")),
        http_timeout_seconds=float(_get_value(dotenv, "HTTP_TIMEOUT_SECONDS", "12")),
        p2p_sample_size=int(_get_value(dotenv, "P2P_SAMPLE_SIZE", "5")),
    )


def _parse_int_set(raw_value: str) -> frozenset[int]:
    values: set[int] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if item:
            values.add(int(item))
    return frozenset(values)
