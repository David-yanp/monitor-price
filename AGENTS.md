# Project Memory

- This is a new Python project for monitoring crypto/CNY price differences.
- Keep features modular and independently extensible: configuration, price providers, storage, alerts, bot commands, and scheduling should stay separated.
- Prefer `asyncio` for concurrency. Network I/O should be async, and long-running services should run as cooperative tasks.
- Keep the implementation simple and efficient. Avoid framework-heavy designs unless the project clearly needs them later.
- Telegram bot token is read from `bot.txt`. Do not hard-code credentials in source files.
- `/query` must always query live prices and reply to the requesting chat, independent of the configured alert chat.
- Alert chat setup should be self-service through Telegram commands when possible. Prefer `/chatid`, `/setalert`, and SQLite-backed runtime settings over requiring manual chat_id discovery.
- The service is expected to run continuously under systemd, with uWSGI used as the service supervisor wrapper for deployment.
- Production service processes must run as `www-data`, not `root`. Keep systemd `User`/`Group` and uWSGI `uid`/`gid` aligned, and ensure runtime files are readable/writable by `www-data`.
- The default alert rule is `abs(C2C_CNY_USDT - Google_USD_CNY) > 0.04`.
