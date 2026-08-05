# Portfolio Project

## LogPulse Sentinel

A local-first background monitoring service that reads application and server logs, detects failures using configurable rules, groups repeated errors into incidents, tracks recovery, and sends optional Telegram alerts.

## Problem

Operational logs often contain thousands of repeated messages. Important failures and recovery events are difficult to notice without a commercial monitoring platform.

## Solution

LogPulse Sentinel converts raw log lines into an incident lifecycle:

- detection;
- grouping and fingerprinting;
- deduplication;
- repeat counting;
- acknowledgement;
- automatic recovery;
- MTTR calculation;
- history and reporting.

## Technologies

Python, FastAPI, SQLite, regular expressions, asyncio, Jinja2, Telegram Bot API, XlsxWriter, Pytest, Docker.

## Demonstrated skills

Background services, file monitoring, log rotation handling, state machines, event normalization, privacy filtering, REST APIs, database design, notification integrations, reporting, testing, and deployment packaging.

## Status

Personal demonstration project. No client data is included.
