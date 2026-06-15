from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.models.user import User
from app.models.voice import Voice
from tests.test_auth import activate, login, register


DESIGN_PAYLOAD = {
    "voiceName": "Nữ trẻ nhẹ nhàng",
    "language": "English",
    "gender": "Female / 女",
    "age": "Young Adult / 青年",
    "pitch": "Moderate Pitch / 中音调",
    "style": "Auto",
    "englishAccent": "American Accent / 美式口音",
    "chineseDialect": None,
}


@pytest.fixture
def voice_storage(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        upload_dir=str(tmp_path),
        max_audio_file_size_mb=1,
    )
    monkeypatch.setattr("app.services.voice_service.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.voices.get_settings", lambda: settings)
    return settings


def prepare_user(
    client,
    db,
    username="demo",
    email="demo@example.com",
    clone_limit=2,
    design_limit=2,
):
    register(client, username=username, email=email)
    user = activate(db, username=username, clone_voice=True, design_voice=True)
    user.voice_clone.number_limit = clone_limit
    user.voice_design.number_limit = design_limit
    db.commit()
    token = login(client, username=username).json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def create_design(client, headers, **overrides):
    payload = {**DESIGN_PAYLOAD, **overrides}
    return client.post("/api/voices/design", headers=headers, json=payload)


def create_clone(client, headers, voice_name="Giọng của tôi", content=b"audio-data"):
    return client.post(
        "/api/voices/clone",
        headers=headers,
        data={"voiceName": voice_name},
        files={"audioFile": ("sample.wav", content, "audio/wav")},
    )


def test_create_clone_voice_saves_safe_file(client, db, voice_storage):
    user, headers = prepare_user(client, db)

    response = create_clone(client, headers)

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == str(user.public_id)
    assert body["voiceName"] == "Giọng của tôi"
    assert body["generationMethod"] == "voice-clone"
    assert body["originalFileName"] == "sample.wav"
    assert body["audioUrl"].endswith("/audio")
    voice = db.query(Voice).one()
    assert voice.storage_key != "sample.wav"
    assert (Path(voice_storage.upload_dir) / voice.storage_key).read_bytes() == b"audio-data"


def test_clone_rejects_invalid_file_and_large_file(client, db, voice_storage):
    _, headers = prepare_user(client, db)

    invalid = client.post(
        "/api/voices/clone",
        headers=headers,
        data={"voiceName": "Invalid"},
        files={"audioFile": ("sample.txt", b"text", "text/plain")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_AUDIO_FILE"

    voice_storage.max_audio_file_size_mb = 0
    too_large = create_clone(client, headers, voice_name="Too large")
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "FILE_TOO_LARGE"


def test_create_design_validates_options(client, db, voice_storage):
    _, headers = prepare_user(client, db)

    response = create_design(client, headers)
    invalid = create_design(
        client,
        headers,
        voiceName="Chinese voice",
        language="Chinese",
        englishAccent=None,
        chineseDialect=None,
    )

    assert response.status_code == 200
    assert response.json()["generationMethod"] == "voice-design"
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_DESIGN_OPTIONS"


def test_voice_name_is_unique_per_user_case_insensitive(client, db, voice_storage):
    _, headers = prepare_user(client, db)
    assert create_design(client, headers, voiceName="My Voice").status_code == 200

    duplicate = create_clone(client, headers, voice_name="  my voice  ")

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "VOICE_NAME_EXISTS"


def test_quota_is_enforced_by_server(client, db, voice_storage):
    _, headers = prepare_user(client, db, clone_limit=1)
    assert create_clone(client, headers, voice_name="First").status_code == 200

    response = create_clone(client, headers, voice_name="Second")
    quota = client.get(
        "/api/voices/limit", headers=headers, params={"type": "voice-clone"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "VOICE_LIMIT_REACHED"
    assert quota.json() == {"current": 1, "limit": 1, "remaining": 0}


def test_create_requires_method_permission(client, db, voice_storage):
    _, headers = prepare_user(client, db)
    user = db.query(User).filter_by(username="demo").one()
    user.clone_voice = False
    db.commit()

    response = create_clone(client, headers)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_list_search_filter_and_pagination(client, db, voice_storage):
    _, headers = prepare_user(client, db, design_limit=3)
    create_design(client, headers, voiceName="Giọng Một")
    create_design(client, headers, voiceName="Giọng Hai")
    create_clone(client, headers, voice_name="Clone Voice")

    response = client.get(
        "/api/voices",
        headers=headers,
        params={
            "page": 1,
            "pageSize": 1,
            "type": "voice-design",
            "search": "Giọng",
        },
    )

    assert response.status_code == 200
    assert response.json()["pageSize"] == 1
    assert response.json()["totalItems"] == 2
    assert response.json()["totalPages"] == 2
    assert "audioFile" not in response.json()["items"][0]


def test_detail_and_rename_are_owner_only(client, db, voice_storage):
    _, owner_headers = prepare_user(client, db)
    created = create_design(client, owner_headers).json()
    voice_id = created["id"]

    _, other_headers = prepare_user(
        client,
        db,
        username="other",
        email="other@example.com",
    )
    forbidden_detail = client.get(f"/api/voices/{voice_id}", headers=other_headers)
    renamed = client.patch(
        f"/api/voices/{voice_id}",
        headers=owner_headers,
        json={"voiceName": "Tên mới"},
    )

    assert forbidden_detail.status_code == 404
    assert forbidden_detail.json()["code"] == "VOICE_NOT_FOUND"
    assert renamed.status_code == 200
    assert renamed.json()["voiceName"] == "Tên mới"


def test_rename_rejects_duplicate_name(client, db, voice_storage):
    _, headers = prepare_user(client, db, design_limit=3)
    first = create_design(client, headers, voiceName="First").json()
    second = create_design(client, headers, voiceName="Second").json()

    response = client.patch(
        f"/api/voices/{second['id']}",
        headers=headers,
        json={"voiceName": first["voiceName"].upper()},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "VOICE_NAME_EXISTS"


def test_audio_stream_and_delete_remove_file(client, db, voice_storage):
    _, headers = prepare_user(client, db)
    created = create_clone(client, headers).json()
    voice = db.query(Voice).filter_by(id=UUID(created["id"])).one()
    stored_path = Path(voice_storage.upload_dir) / voice.storage_key

    audio = client.get(created["audioUrl"], headers=headers)
    deleted = client.delete(f"/api/voices/{created['id']}", headers=headers)

    assert audio.status_code == 200
    assert audio.content == b"audio-data"
    assert audio.headers["content-type"].startswith("audio/wav")
    assert deleted.status_code == 204
    assert not stored_path.exists()
    assert client.get(f"/api/voices/{created['id']}", headers=headers).status_code == 404


def test_voice_api_returns_unified_unauthorized_error(client):
    response = client.get("/api/voices")

    assert response.status_code == 401
    assert response.json() == {
        "code": "UNAUTHORIZED",
        "message": "Yêu cầu đăng nhập.",
        "details": None,
    }
