import json
from types import SimpleNamespace

import app.core.audit as audit
from tests.test_auth import activate, login, register


def configure_audit(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        audit_log_enabled=True,
        audit_log_dir=str(tmp_path),
        audit_log_max_bytes=1024 * 1024,
        audit_log_backup_count=2,
    )
    audit.get_audit_logger.cache_clear()
    monkeypatch.setattr(audit, "get_settings", lambda: settings)
    return settings


def read_events(log_dir):
    events = []
    for path in log_dir.glob("*.log"):
        events.extend(json.loads(line) for line in path.read_text().splitlines())
    return events


def test_audit_log_is_split_by_user_and_hides_secrets(client, db, tmp_path, monkeypatch):
    settings = configure_audit(tmp_path, monkeypatch)
    register(client)
    activate(db)
    login_response = login(client)
    token = login_response.json()["access_token"]
    client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    register(client, username="other", email="other@example.com")

    audit.get_audit_logger().close()
    events = read_events(tmp_path)
    files = list(tmp_path.glob("*.log"))
    content = "\n".join(path.read_text() for path in files)

    assert len(files) == 2
    assert {event["path"] for event in events} >= {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
    }
    assert all("requestId" in event for event in events)
    assert all("durationMs" in event for event in events)
    assert "password123" not in content
    assert token not in content
    assert "Authorization" not in content

    audit.get_audit_logger.cache_clear()


def test_anonymous_api_call_has_separate_log(client, tmp_path, monkeypatch):
    configure_audit(tmp_path, monkeypatch)

    response = client.get("/api/voices")

    audit.get_audit_logger().close()
    events = read_events(tmp_path)
    assert response.status_code == 401
    assert events[0]["path"] == "/api/voices"
    assert events[0]["statusCode"] == 401
    assert events[0]["userId"] is None
    audit.get_audit_logger.cache_clear()
