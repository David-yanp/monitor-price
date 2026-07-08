from __future__ import annotations

from pathlib import Path
import sqlite3

from app.models import PriceSnapshot


SCHEMA = """
CREATE TABLE IF NOT EXISTS price_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL,
    c2c_source TEXT,
    c2c_price REAL,
    usd_cny_rate REAL,
    diff REAL,
    threshold REAL NOT NULL,
    alert_sent INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_check_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_check_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    c2c_price REAL NOT NULL,
    diff REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_check_id) REFERENCES price_checks(id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class PriceStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    async def init(self) -> None:
        self._init_sync()

    def _init_sync(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    async def record_success(
        self,
        snapshot: PriceSnapshot,
        threshold: float,
        alert_sent: bool,
    ) -> None:
        self._record_success_sync(snapshot, threshold, alert_sent)

    def _record_success_sync(
        self,
        snapshot: PriceSnapshot,
        threshold: float,
        alert_sent: bool,
    ) -> None:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_checks (
                    checked_at, c2c_source, c2c_price, usd_cny_rate, diff, threshold, alert_sent, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    snapshot.checked_at.isoformat(),
                    snapshot.c2c_source,
                    snapshot.c2c_price,
                    snapshot.usd_cny_rate,
                    snapshot.diff,
                    threshold,
                    1 if alert_sent else 0,
                ),
            )
            price_check_id = int(cursor.lastrowid)
            conn.executemany(
                """
                INSERT INTO price_check_sources (
                    price_check_id, source, c2c_price, diff
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (price_check_id, quote.source, quote.price, quote.diff)
                    for quote in snapshot.quotes
                ),
            )
            conn.commit()

    async def get_setting(self, key: str) -> str | None:
        return self._get_setting_sync(key)

    def _get_setting_sync(self, key: str) -> str | None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row[0])

    async def set_setting(self, key: str, value: str) -> None:
        self._set_setting_sync(key, value)

    def _set_setting_sync(self, key: str, value: str) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            conn.commit()

    async def record_error(self, threshold: float, error: str) -> None:
        self._record_error_sync(threshold, error)

    def _record_error_sync(self, threshold: float, error: str) -> None:
        from datetime import datetime, timezone

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO price_checks (
                    checked_at, threshold, alert_sent, error
                ) VALUES (?, ?, 0, ?)
                """,
                (datetime.now(timezone.utc).isoformat(), threshold, error[:1000]),
            )
            conn.commit()
