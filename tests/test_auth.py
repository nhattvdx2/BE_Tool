from app.core.security import hash_password
from app.models.user import User
from app.models.voice import VoiceClone, VoiceDesign


def register(client, username="demo", email="demo@example.com"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )


def activate(db, username="demo", **permissions):
    user = db.query(User).filter_by(username=username).one()
    user.is_active = True
    for key, value in permissions.items():
        setattr(user, key, value)
    db.commit()
    return user


def login(client, username="demo", password="password123"):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def test_register_creates_inactive_user_and_voice_limits(client, db):
    response = register(client)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    user = db.query(User).filter_by(username="demo").one()
    assert db.query(VoiceClone).filter_by(user_id=user.id).count() == 1
    assert db.query(VoiceDesign).filter_by(user_id=user.id).count() == 1


def test_login_requires_active_user_and_returns_jwt(client, db):
    register(client)
    assert login(client).status_code == 401
    activate(db)

    response = login(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_me_and_change_password(client, db):
    register(client)
    activate(db)
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    changed = client.post(
        "/api/auth/changepassword",
        headers=headers,
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert changed.status_code == 200
    assert login(client, password="newpassword123").status_code == 200


def test_duplicate_registration_is_rejected(client):
    assert register(client).status_code == 200
    assert register(client).status_code == 409
