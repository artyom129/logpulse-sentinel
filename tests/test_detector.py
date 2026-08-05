from app.detector import Detector


def test_detects_incident_and_redacts_sensitive_values(settings):
    detector = Detector(settings)
    result = detector.detect(
        "ERROR payment gateway timeout user=test@example.com "
        "ip=192.168.1.10 token=very-secret-token"
    )
    assert result is not None
    assert result.rule_id == "payment_failure"
    assert result.kind == "incident"
    assert "test@example.com" not in result.message
    assert "192.168.1.10" not in result.message
    assert "very-secret-token" not in result.message


def test_detects_recovery(settings):
    detector = Detector(settings)
    result = detector.detect("INFO database connection recovered and healthy")
    assert result is not None
    assert result.rule_id == "database_timeout"
    assert result.kind == "recovery"


def test_ignores_unmatched_info_line(settings):
    detector = Detector(settings)
    assert detector.detect("INFO request completed status=200") is None
