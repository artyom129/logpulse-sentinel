<a id="english"></a>

<div align="center">

**🇬🇧 English** · [🇷🇺 Русский](#russian)

# LogPulse Sentinel

### Real-time log monitoring, incident grouping, recovery tracking, and Telegram alerts

**Python · FastAPI · SQLite · Background Monitoring · Excel Reports**

</div>

LogPulse Sentinel is a production-style local monitoring service that watches application or server log files, detects meaningful failures, groups repeated errors into incidents, tracks recoveries, and provides a clean dashboard with history and exports.

It is built around the same practical idea as a useful background script: run quietly, collect events automatically, avoid duplicate alerts, keep history, and show the result only when it matters.

## What it solves

Raw logs are noisy. One database outage can produce hundreds of nearly identical lines, while an important recovery message may be buried later in the file.

LogPulse Sentinel converts that stream into a small number of understandable incidents:

```text
1,240 repeated log lines
            ↓
3 grouped incidents
            ↓
1 Telegram alert per incident
            ↓
automatic recovery and MTTR tracking
```

## Features

- Watches multiple log files in the background
- Handles file truncation and log rotation
- Detects incidents using configurable regular expressions
- Groups repeated errors by stable fingerprints
- Deduplicates noisy alerts during a configurable time window
- Tracks first seen, last seen, repeat count, status, and recovery time
- Calculates mean time to recovery
- Supports manual acknowledgement and resolution
- Stores incident and event history in SQLite
- Provides a responsive FastAPI dashboard
- Exposes a REST ingestion endpoint for webhooks and external tools
- Exports incident reports to CSV and formatted Excel
- Sends optional Telegram alerts
- Supports Telegram commands: `/status`, `/open`, `/today`
- Includes privacy redaction for tokens, emails, and IP addresses
- Includes sample rules, demo logs, Docker, and automated tests
- Uses no paid APIs

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py
python run.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python seed_demo.py
python run.py
```

Open `http://127.0.0.1:8000` and API docs at `http://127.0.0.1:8000/docs`.

## Demo workflow

```bash
python seed_demo.py
python scripts/generate_demo_log.py
```

## Tests

```bash
pytest -q
```

## Portfolio context

This is a personal demonstration project. It contains no client data and does not claim to be client work.

## License

MIT

---

<a id="russian"></a>

<div align="center">

[🇬🇧 English](#english) · **🇷🇺 Русский**

</div>

# LogPulse Sentinel — Русская версия

Фоновый сервис, который следит за логами приложений и серверов, превращает повторяющийся поток ошибок в понятные инциденты, отслеживает восстановление и отправляет уведомления в Telegram.

## Основная идея

Сервис работает постоянно и автоматически:

1. читает новые строки из нескольких лог-файлов;
2. определяет ошибки по настраиваемым правилам;
3. объединяет одинаковые ошибки в один инцидент;
4. не отправляет сотни одинаковых уведомлений;
5. хранит историю в SQLite;
6. закрывает инцидент после строки о восстановлении;
7. показывает статистику и MTTR в веб-панели;
8. выгружает CSV и Excel.

## Запуск

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py
python run.py
```

Панель:

```text
http://127.0.0.1:8000
```

Генератор тестовых логов:

```bat
python scripts\generate_demo_log.py
```

## Что демонстрирует проект

- файловый мониторинг;
- обработку ротации логов;
- регулярные выражения;
- дедупликацию событий;
- управление состояниями инцидента;
- SQLite;
- FastAPI;
- Telegram Bot API;
- CSV/Excel-отчёты;
- Docker;
- автоматические тесты.
