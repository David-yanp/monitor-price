# Crypto Price Monitor

Async Python service for monitoring the CNY/USDT C2C price against the Google USD/CNY rate.

## Runtime Layout

Recommended production layout:

- code: `/opt/monitor-price`, read-only for the service user
- config: `/etc/monitor-price`, stores `.env` and `bot.txt`
- data: `/var/lib/monitor-price`, stores `prices.db`
- process user: `www-data`

This keeps Git operations, secrets, runtime data, and the service identity separated.

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
DATABASE_PATH=/var/lib/monitor-price/prices.db
BOT_TOKEN_FILE=/etc/monitor-price/bot.txt
```

`bot.txt` must contain the Telegram bot token. In production, place it at `/etc/monitor-price/bot.txt`.

`TELEGRAM_CHAT_ID` is optional. You can start the bot, send `/setalert` from Telegram, and the bot will save the current chat as the alert target in SQLite.

## Run Locally

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

Install uWSGI from system packages:

```bash
sudo apt install uwsgi uwsgi-plugin-python3
```

Install code and dependencies:

```bash
sudo mkdir -p /opt/monitor-price /etc/monitor-price /var/lib/monitor-price
sudo rsync -a --delete --exclude .git --exclude .venv --exclude bot.txt --exclude prices.db ./ /opt/monitor-price/
sudo python3 -m venv /opt/monitor-price/.venv
sudo /opt/monitor-price/.venv/bin/python -m pip install -r /opt/monitor-price/requirements.txt
```

Install config and runtime data:

```bash
sudo cp /opt/monitor-price/.env.example /etc/monitor-price/.env
sudo install -m 0640 -o root -g www-data bot.txt /etc/monitor-price/bot.txt
sudo chown -R www-data:www-data /var/lib/monitor-price
sudo chmod 750 /var/lib/monitor-price
```

Install service files:

```bash
sudo cp /opt/monitor-price/deploy/monitor_price.uwsgi.ini.example /etc/monitor-price/monitor_price.uwsgi.ini
sudo cp /opt/monitor-price/deploy/monitor-price.service.example /etc/systemd/system/monitor-price.service
sudo chown -R root:root /opt/monitor-price
sudo find /opt/monitor-price -type d -exec chmod 755 {} \;
sudo find /opt/monitor-price -type f -exec chmod 644 {} \;
sudo chown -R root:www-data /etc/monitor-price
sudo chmod 750 /etc/monitor-price
sudo chmod 640 /etc/monitor-price/*
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

SQLite defaults to `/var/lib/monitor-price/prices.db`. Each monitor run records successful checks and failures in `price_checks`.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
