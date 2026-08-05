from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import Settings, load_settings
from .database import (
    acknowledge_incident,
    dashboard_stats,
    get_incident,
    init_db,
    list_incidents,
    recent_events,
    resolve_incident,
)
from .engine import IncidentEngine
from .exporter import incidents_to_csv, incidents_to_xlsx
from .monitor import LogMonitor
from .telegram import TelegramClient


BASE_DIR = Path(__file__).resolve().parent


class IngestRequest(BaseModel):
    source: str = Field(min_length=1, max_length=500)
    line: str = Field(min_length=1, max_length=20000)
    created_at: str | None = None


def create_app(
    config_path: str | Path | None = None,
    *,
    settings_override: Settings | None = None,
) -> FastAPI:
    settings = settings_override or load_settings(config_path)
    init_db(settings.database_path)

    telegram = TelegramClient(
        settings,
        stats_provider=lambda: dashboard_stats(settings.database_path),
    )
    engine = IncidentEngine(settings, notifier=telegram.send)
    monitor = LogMonitor(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop = asyncio.Event()

        async def monitor_loop():
            while not stop.is_set():
                await asyncio.to_thread(monitor.tick)
                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=settings.scan_interval_seconds
                    )
                except asyncio.TimeoutError:
                    pass

        async def telegram_loop():
            while not stop.is_set():
                if telegram.enabled:
                    await asyncio.to_thread(telegram.poll_once)
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        timeout=settings.telegram_poll_interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass

        tasks = [asyncio.create_task(monitor_loop())]
        if settings.telegram_enabled and settings.telegram_poll_commands:
            tasks.append(asyncio.create_task(telegram_loop()))

        yield
        stop.set()
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title=settings.app_name,
        description="Real-time log monitoring and incident grouping service.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.monitor = monitor
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        rows = list_incidents(
            settings.database_path,
            limit=settings.max_incidents_on_dashboard,
        )
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "app_name": settings.app_name,
                "rows": rows,
                "stats": dashboard_stats(settings.database_path),
                "events": recent_events(settings.database_path, 12),
            },
        )

    @app.get("/incidents", response_class=HTMLResponse)
    async def incidents_page(
        request: Request,
        status: str | None = Query(default=None),
        severity: str | None = Query(default=None),
        q: str | None = Query(default=None),
    ):
        rows = list_incidents(
            settings.database_path,
            status=status or None,
            severity=severity or None,
            query=q or None,
        )
        return templates.TemplateResponse(
            request=request,
            name="incidents.html",
            context={
                "app_name": settings.app_name,
                "rows": rows,
                "status": status or "",
                "severity": severity or "",
                "q": q or "",
            },
        )

    @app.get("/incidents/{incident_id}", response_class=HTMLResponse)
    async def incident_detail(request: Request, incident_id: int):
        row = get_incident(settings.database_path, incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        return templates.TemplateResponse(
            request=request,
            name="detail.html",
            context={"app_name": settings.app_name, "row": row},
        )

    @app.post("/incidents/{incident_id}/acknowledge")
    async def acknowledge_from_ui(incident_id: int):
        if not get_incident(settings.database_path, incident_id):
            raise HTTPException(status_code=404, detail="Incident not found")
        acknowledge_incident(settings.database_path, incident_id)
        return RedirectResponse(f"/incidents/{incident_id}", status_code=303)

    @app.post("/incidents/{incident_id}/resolve")
    async def resolve_from_ui(incident_id: int):
        if not get_incident(settings.database_path, incident_id):
            raise HTTPException(status_code=404, detail="Incident not found")
        resolve_incident(settings.database_path, incident_id)
        return RedirectResponse(f"/incidents/{incident_id}", status_code=303)

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "app_name": settings.app_name,
                "settings": settings,
            },
        )

    @app.post("/api/ingest")
    async def api_ingest(payload: IngestRequest):
        result = engine.ingest_line(
            payload.source,
            payload.line,
            created_at=payload.created_at,
        )
        return {"matched": result is not None, "result": result}

    @app.get("/api/incidents")
    async def api_incidents(
        status: str | None = None,
        severity: str | None = None,
        q: str | None = None,
        limit: int = 200,
    ):
        return {
            "items": list_incidents(
                settings.database_path,
                status=status,
                severity=severity,
                query=q,
                limit=min(max(limit, 1), 10000),
            ),
            "stats": dashboard_stats(settings.database_path),
        }

    @app.get("/api/incidents/{incident_id}")
    async def api_incident(incident_id: int):
        row = get_incident(settings.database_path, incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        return row

    @app.post("/api/incidents/{incident_id}/acknowledge")
    async def api_acknowledge(incident_id: int):
        if not get_incident(settings.database_path, incident_id):
            raise HTTPException(status_code=404, detail="Incident not found")
        changed = acknowledge_incident(settings.database_path, incident_id)
        return {"changed": changed}

    @app.post("/api/incidents/{incident_id}/resolve")
    async def api_resolve(incident_id: int):
        if not get_incident(settings.database_path, incident_id):
            raise HTTPException(status_code=404, detail="Incident not found")
        changed = resolve_incident(settings.database_path, incident_id)
        return {"changed": changed}

    @app.get("/api/stats")
    async def api_stats():
        return dashboard_stats(settings.database_path)

    @app.get("/exports/incidents.csv")
    async def export_csv():
        rows = list_incidents(settings.database_path, limit=10000)
        return Response(
            incidents_to_csv(rows),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=logpulse_incidents.csv"
            },
        )

    @app.get("/exports/incidents.xlsx")
    async def export_xlsx():
        rows = list_incidents(settings.database_path, limit=10000)
        return Response(
            incidents_to_xlsx(rows),
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": "attachment; filename=logpulse_incidents.xlsx"
            },
        )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "monitored_files": len(settings.monitored_files),
            "telegram_enabled": telegram.enabled,
        }

    return app


app = create_app()
