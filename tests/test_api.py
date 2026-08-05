from fastapi.testclient import TestClient

from app.main import create_app


def test_ingest_and_incident_workflow(settings):
    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        response = client.post(
            "/api/ingest",
            json={
                "source": "checkout.log",
                "line": "ERROR payment gateway timeout order=8172",
            },
        )
        assert response.status_code == 200
        result = response.json()["result"]
        incident_id = result["incident_id"]

        detail = client.get(f"/api/incidents/{incident_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "open"

        ack = client.post(f"/api/incidents/{incident_id}/acknowledge")
        assert ack.json()["changed"] is True

        resolved = client.post(f"/api/incidents/{incident_id}/resolve")
        assert resolved.json()["changed"] is True

        xlsx = client.get("/exports/incidents.xlsx")
        assert xlsx.status_code == 200
        assert xlsx.content.startswith(b"PK")


def test_unmatched_line_is_not_incident(settings):
    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            json={"source": "app.log", "line": "INFO request completed status=200"},
        )
        assert response.json() == {"matched": False, "result": None}
