import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_auth.db")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test")
    monkeypatch.setenv("META_APP_SECRET", "test")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_must_be_long_enough_32c")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    # hash de "testpass"
    monkeypatch.setenv(
        "ADMIN_PASSWORD_HASH",
        "$2b$12$KIXtyPOYsDMHLmQnlMt7sOrZPGTtRBGfZNdUNPHPEBVxqsRhLWkPi",
    )


class TestLogin:
    def test_valid_credentials_return_token(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "testpass"},
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
            json={"username": "hacker", "password": "testpass"},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    def _get_token(self) -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "testpass"},
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
        response = client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test",
                "hub.challenge": "42",
            },
        )
        assert response.status_code == 200
