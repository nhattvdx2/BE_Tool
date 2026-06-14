from app.models.user import User

from tests.test_auth import activate, login, register


def test_accept_function_and_number_limit(client, db):
    register(client)
    user = activate(db, clone_voice=True)
    user.voice_clone.number_limit = 12
    db.commit()
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    access = client.post(
        "/api/auth/acceptFuntion",
        headers=headers,
        json={"username": "demo", "screenid": "clone_voice"},
    )
    limit = client.get(
        "/api/voices/numberLimit",
        headers=headers,
        params={"username": "demo", "screenid": "clone_voice"},
    )

    assert access.json()["allowed"] is True
    assert limit.status_code == 200
    assert limit.json()["number_limit"] == 12


def test_design_voice_is_enabled_by_default(client, db):
    register(client)
    activate(db)
    token = login(client).json()["access_token"]

    response = client.get(
        "/api/voices/numberLimit",
        headers={"Authorization": f"Bearer {token}"},
        params={"username": "demo", "screenid": "design_voice"},
    )

    assert response.status_code == 200
    assert response.json()["number_limit"] == 0


def test_gen_voice_has_access_but_no_number_limit(client, db):
    register(client)
    activate(db)
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    access = client.post(
        "/api/auth/acceptFuntion",
        headers=headers,
        json={"username": "demo", "screenid": "gen_voice"},
    )
    limit = client.get(
        "/api/voices/numberLimit",
        headers=headers,
        params={"username": "demo", "screenid": "gen_voice"},
    )

    assert access.json()["allowed"] is True
    assert limit.status_code == 400


def test_upload_voice_file(client, db, tmp_path, monkeypatch):
    register(client)
    activate(db, clone_voice=True)
    token = login(client).json()["access_token"]
    monkeypatch.setattr(
        "app.api.routes.voices.get_settings",
        lambda: type("Settings", (), {"upload_dir": str(tmp_path)})(),
    )

    response = client.post(
        "/api/voices/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"screenid": "clone_voice"},
        files={"upload": ("sample.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json()["size"] == 10
    assert (tmp_path / "demo").exists()
