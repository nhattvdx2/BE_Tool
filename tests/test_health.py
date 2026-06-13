from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "schema": "ok",
    }


def test_database_error_returns_service_unavailable(client):
    def fail():
        raise OperationalError("SELECT 1", {}, Exception("database unavailable"))
        yield

    app.dependency_overrides[get_db] = fail

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert "alembic upgrade head" in response.json()["detail"]
