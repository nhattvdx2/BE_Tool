from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.core.security import decode_access_token, hash_password, verify_password
from app.models.user import User
from app.models.user_admin import UserAdmin
from app.models.voice import Voice
from tests.test_auth import activate, login, register
from tests.test_voices import create_clone, create_design, prepare_user


@pytest.fixture
def voice_storage(tmp_path, monkeypatch):
    settings = SimpleNamespace(upload_dir=str(tmp_path), max_audio_file_size_mb=1)
    monkeypatch.setattr("app.services.voice_service.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.voices.get_settings", lambda: settings)
    return settings


def admin_headers(client, db):
    admin = UserAdmin(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add(admin)
    db.commit()
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    token = response.json()["access_token"]
    return admin, {"Authorization": f"Bearer {token}"}


def test_admin_page_and_static_assets_are_public(client):
    page = client.get("/admin")
    stylesheet = client.get("/static/admin/admin.css")

    assert page.status_code == 200
    assert "Quản trị hệ thống" in page.text
    assert "/static/admin/admin.css?v=3" in page.text
    assert stylesheet.status_code == 200
    assert "[hidden]{display:none!important}" in stylesheet.text
    assert ".sidebar-footer{display:flex" in stylesheet.text


def test_admin_api_requires_admin_permission(client, db):
    assert client.get("/api/admin/dashboard").status_code == 401
    register(client)
    activate(db)
    token = login(client).json()["access_token"]

    response = client.get(
        "/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin access token"


def test_admin_login_is_separate_from_user_login(client, db):
    admin, headers = admin_headers(client, db)
    token = headers["Authorization"].removeprefix("Bearer ")

    assert client.get("/api/admin/dashboard", headers=headers).status_code == 200
    assert login(client, username=admin.username).status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert decode_access_token(token)["account_type"] == "admin"


def test_dashboard_and_user_management(client, db):
    admin, headers = admin_headers(client, db)
    register(client)

    dashboard = client.get("/api/admin/dashboard", headers=headers)
    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "operator",
            "email": "operator@example.com",
            "password": "password123",
            "is_active": True,
            "clone_voice": True,
            "clone_limit": 4,
            "design_limit": 7,
        },
    )
    user_id = created.json()["id"]
    updated = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"is_active": False, "clone_limit": 9, "gen_voice": False},
    )
    listed = client.get(
        "/api/admin/users", headers=headers, params={"search": "operator"}
    )

    assert dashboard.status_code == 200
    assert dashboard.json()["total_users"] == 1
    assert dashboard.json()["admin_users"] == 1
    assert created.status_code == 201
    assert created.json()["clone_limit"] == 4
    assert updated.json()["is_active"] is False
    assert updated.json()["clone_limit"] == 9
    assert updated.json()["gen_voice"] is False
    assert listed.json()["total_items"] == 1
    assert listed.json()["items"][0]["username"] == "operator"
    assert admin.is_active is True


def test_admin_can_reset_normal_user_password(client, db):
    _, headers = admin_headers(client, db)
    register(client)
    user = activate(db)
    reset = client.post(
        f"/api/admin/users/{user.id}/reset-password",
        headers=headers,
        json={"new_password": "newpassword123"},
    )

    db.refresh(user)
    assert reset.status_code == 200
    assert verify_password("newpassword123", user.password_hash)


def test_admin_manages_all_voices_and_removes_audio_file(
    client, db, voice_storage, monkeypatch
):
    _, owner_headers = prepare_user(client, db)
    design = create_design(client, owner_headers).json()
    clone = create_clone(client, owner_headers).json()
    clone_model = db.query(Voice).filter_by(id=UUID(clone["id"])).one()
    stored_path = Path(voice_storage.upload_dir) / clone_model.storage_key
    _, headers = admin_headers(client, db)
    monkeypatch.setattr("app.services.admin_service.get_settings", lambda: voice_storage)
    monkeypatch.setattr("app.api.routes.admin.get_settings", lambda: voice_storage)

    listed = client.get("/api/admin/voices", headers=headers)
    renamed = client.patch(
        f"/api/admin/voices/{design['id']}",
        headers=headers,
        json={"voiceName": "Admin renamed"},
    )
    audio = client.get(f"/api/admin/voices/{clone['id']}/audio", headers=headers)
    deleted = client.delete(f"/api/admin/voices/{clone['id']}", headers=headers)

    assert listed.status_code == 200
    assert listed.json()["total_items"] == 2
    assert {item["owner_username"] for item in listed.json()["items"]} == {"demo"}
    assert renamed.json()["voice_name"] == "Admin renamed"
    assert audio.content == b"audio-data"
    assert deleted.status_code == 204
    assert not stored_path.exists()


def test_admin_audit_endpoint_handles_disabled_logging(client, db):
    _, headers = admin_headers(client, db)

    response = client.get("/api/admin/audit", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"items": []}
