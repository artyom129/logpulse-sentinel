<div align="center">

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
