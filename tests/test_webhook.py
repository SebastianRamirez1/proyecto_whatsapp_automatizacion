import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VERIFY_TOKEN = "test_verify_token"
APP_SECRET = "test_app_secret"


def make_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("META_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("SECRET_KEY", "test_secret_32_chars_long_padded")


class TestWebhookVerification:
    def test_valid_verification(self):
        response = client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "12345",
            },
        )
        assert response.status_code == 200
        assert response.json() == 12345

    def test_invalid_token_returns_403(self):
        response = client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "12345",
            },
        )
        assert response.status_code == 403


class TestWebhookReceiver:
    def _build_payload(self, message_body: str) -> dict:
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "123"},
                                "contacts": [{"profile": {"name": "Test"}, "wa_id": "573001234567"}],
                                "messages": [
                                    {
                                        "from": "573001234567",
                                        "id": "wamid.abc123",
                                        "timestamp": "1700000000",
                                        "type": "text",
                                        "text": {"body": message_body},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

    def test_valid_message_returns_200(self):
        payload = json.dumps(self._build_payload("Quiero 2 cubetas de huevos")).encode()
        signature = make_signature(payload, APP_SECRET)
        response = client.post(
            "/api/v1/webhook",
            content=payload,
            headers={"content-type": "application/json", "x-hub-signature-256": signature},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    def test_invalid_signature_returns_401(self):
        payload = json.dumps(self._build_payload("Hola")).encode()
        response = client.post(
            "/api/v1/webhook",
            content=payload,
            headers={"content-type": "application/json", "x-hub-signature-256": "sha256=invalid"},
        )
        assert response.status_code == 401
