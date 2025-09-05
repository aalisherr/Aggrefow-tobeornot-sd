## Crypto Announcements Aggregator (Async, Microservice-Ready)

This project asynchronously scrapes and aggregates announcements from major crypto exchanges and notifies a Telegram group (with per-exchange topics). It stores only new announcements in SQLite via aiosqlite, supports proxy rotation, and is designed with modular scrapers per exchange.

### Features
- Async I/O with `aiohttp` and `aiosqlite`
- Pluggable exchange scrapers (`Binance` implemented; `Bybit`, `KuCoin` stubs)
- Spot vs Futures listing classification
- Telegram notifier with per-exchange topics (forum mode)
- Proxy rotation (round-robin)
- Only-notify-new announcements (idempotent persistence)
- ActionEngine placeholder for optional buy/sell decisions

### Quick Start
1. Create a virtual environment (optional) and install deps:
```bash
pip install -r requirements.txt
```

2. Set environment variables (example `.env`):
```bash
TELEGRAM_BOT_TOKEN=123:ABC
TELEGRAM_CHAT_ID=-1001234567890
# Optional separate chat to receive demo test messages
TELEGRAM_DEMO_CHAT_ID=-1009876543210
# JSON mapping of exchange name to topic/thread id (forum topic)
TELEGRAM_TOPIC_MAP={"binance": 12345, "bybit": 23456, "kucoin": 34567}

# Comma-separated proxies (optional), e.g. http://user:pass@host:port
PROXIES=http://127.0.0.1:8888,https://proxy.example.com:8443

DB_PATH=announcements.db
POLL_INTERVAL=1
USER_AGENT=Mozilla/5.0 (compatible; ListingsBot/1.0)

# Demo mode to force-send the most recent item for quick verification
DEMO_MODE=false
```

3. Run:
```bash
python -m app.main
```

### Project Structure
```
app/
  __init__.py
  main.py
  config.py
  logging_setup.py
  models.py
  runner.py
  http/
    __init__.py
    client.py
  utils/
    __init__.py
    proxy_rotator.py
  db/
    __init__.py
    repository.py
  notifier/
    __init__.py
    telegram.py
  exchanges/
    __init__.py
    base.py
    binance.py
    bybit.py
    kucoin.py
  actions/
    __init__.py
    engine.py
```

### Notes
- By default, the runner polls every second. Tune `POLL_INTERVAL` as needed.
- Ensure your Telegram supergroup has topics enabled and you know each topic's `message_thread_id`.
- The DB initializes itself on first run; it enforces uniqueness on `(exchange, source_id)`.

### Future Work
- Implement Bybit/KuCoin scrapers and extend classifiers
- Add richer error handling, backoff, and metrics
- Add REST API and background workers if splitting into microservices


