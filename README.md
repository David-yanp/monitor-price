# Crypto Price Monitor

Async Python service for monitoring the CNY/USDT C2C price against the Google USD/CNY rate.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Optional `.env` values:

```bash
TELEGRAM_CHAT_ID=your_alert_chat_id
TELEGRAM_ADMIN_USER_IDS=your_telegram_user_id
```

`bot.txt` must contain the Telegram bot token.

`TELEGRAM_CHAT_ID` is optional. You can start the bot, send `/setalert` from Telegram, and the bot will save the current chat as the alert target in SQLite.

## Run

```bash
.venv/bin/python -m app.main
```

The service runs two concurrent tasks:

- price monitoring every `CHECK_INTERVAL_SECONDS` seconds
- Telegram long polling for bot commands

## Telegram Commands

- `/start` shows available commands
- `/commands` shows available commands
- `/query` fetches live prices and replies with the current absolute price difference
- `/chatid` replies with the current Telegram chat_id and user_id
- `/setalert` saves the current chat as the alert target
- `/status` shows the active alert chat_id

Telegram Bot API cannot list every chat or discover a chat_id only from the bot token. The bot learns chat_id values only after a user, group, or channel sends an update to it. Recommended setup:

1. Start the service.
2. Send `/chatid` to the bot in the private chat or group that should receive alerts.
3. Send `/setalert` in that same chat.
4. If `TELEGRAM_ADMIN_USER_IDS` is set, only those user IDs can run `/setalert`.

For groups, add the bot to the group first. If privacy mode blocks regular messages, commands such as `/chatid` and `/setalert` still reach the bot.

## systemd + uWSGI

Install uWSGI from system packages and Python dependencies into the virtual environment:

```bash
sudo apt install uwsgi uwsgi-plugin-python3
.venv/bin/python -m pip install -r requirements.txt
```

Install the systemd service:

```bash
sudo chown -R www-data:www-data /home/monitor_price
sudo find /home/monitor_price -type d -exec chmod 750 {} \;
sudo find /home/monitor_price -type f -exec chmod 640 {} \;
sudo chmod 750 /home/monitor_price/.venv/bin/*
sudo cp deploy/monitor-price.service /etc/systemd/system/monitor-price.service
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-price.service
```

Check logs:

```bash
sudo journalctl -u monitor-price.service -f
```

The uWSGI config exposes a small local health endpoint on `127.0.0.1:9099` and runs the async monitor as a managed attached daemon.

On startup the service calls Telegram `deleteMyCommands` and `setMyCommands`, so the bot menu is reset to the commands listed above.

## Data

SQLite defaults to `prices.db`. Each monitor run records successful checks and failures in `price_checks`.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
