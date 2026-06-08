import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.main import app

client = TestClient(app)

_TEST_PASSWORD = "testpass"
# Generate fresh hash at import time — avoids hardcoded bcrypt strings that
# can't be verified at a glance and ensures any bcrypt version works.
_TEST_HASH = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(_TEST_PASSWORD)


@pytest.fixture(autouse=True)
def patch_settings():
    """Override settings values for the duration of each test.

    monkeypatch.setattr / setenv do NOT affect pydantic-settings objects
    already instantiated at module import time. Directly mutating __dict__
    (where pydantic v2 stores field values) is the reliable workaround.
    """
    from app.core.config import settings

    orig_hash = settings.ADMIN_PASSWORD_HASH
    orig_username = settings.ADMIN_USERNAME

    settings.__dict__["ADMIN_PASSWORD_HASH"] = _TEST_HASH
    settings.__dict__["ADMIN_USERNAME"] = "admin"

    yield

    settings.__dict__["ADMIN_PASSWORD_HASH"] = orig_hash
    settings.__dict__["ADMIN_USERNAME"] = orig_username


class TestLogin:
    def test_valid_credentials_return_token(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": _TEST_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_wrong_password_returns_401(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_wrong_username_returns_401(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "hacker", "password": _TEST_PASSWORD},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    def _get_token(self) -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": _TEST_PASSWORD},
        )
        return response.json()["access_token"]

    def test_orders_without_token_returns_401(self):
        response = client.get("/api/v1/orders")
        assert response.status_code == 401

    def test_orders_with_valid_token_returns_200(self):
        token = self._get_token()
        response = client.get(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_stats_without_token_returns_401(self):
        response = client.get("/api/v1/orders/summary/stats")
        assert response.status_code == 401

    def test_stats_with_valid_token_returns_200(self):
        token = self._get_token()
        response = client.get(
            "/api/v1/orders/summary/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data

    def test_invalid_token_returns_401(self):
        response = client.get(
            "/api/v1/orders",
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert response.status_code == 401

    def test_health_is_public(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_webhook_get_is_public(self):
        from app.core.config import settings

        response = client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
                "hub.challenge": "42",
            },
        )
        assert response.status_code == 200
