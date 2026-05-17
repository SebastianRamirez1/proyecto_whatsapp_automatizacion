import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.interpretation import MessageIntent, OrderItemExtracted
from app.services.interpretation import (
    build_clarification_message,
    build_confirmation_message,
    interpret_message,
)


def _make_openai_response(data: dict) -> MagicMock:
    """Builds a mock that mimics openai.ChatCompletion response shape."""
    choice = MagicMock()
    choice.message.content = json.dumps(data)
    response = MagicMock()
    response.choices = [choice]
    return response


VALID_ORDER_RESPONSE = {
    "intent": "nuevo_pedido",
    "items": [{"producto": "Huevos AA", "cantidad": 3, "unidad": "cubeta"}],
    "direccion_entrega": "Calle 45 # 12-30",
    "observaciones": None,
    "confianza": 0.95,
    "razon_ambiguo": None,
}

AMBIGUOUS_RESPONSE = {
    "intent": "ambiguo",
    "items": [],
    "direccion_entrega": None,
    "observaciones": None,
    "confianza": 0.3,
    "razon_ambiguo": "No especificaste qué producto o qué cantidad necesitas.",
}

STATUS_QUERY_RESPONSE = {
    "intent": "consulta_estado",
    "items": [],
    "direccion_entrega": None,
    "observaciones": None,
    "confianza": 0.9,
    "razon_ambiguo": None,
}


@pytest.fixture(autouse=True)
def patch_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test")
    monkeypatch.setenv("META_APP_SECRET", "test")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_32_chars_long_pad")


class TestInterpretMessage:
    @pytest.mark.asyncio
    async def test_new_order_parsed_correctly(self):
        mock_response = _make_openai_response(VALID_ORDER_RESPONSE)
        with patch(
            "app.services.interpretation._client.chat.completions.create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await interpret_message("Necesito 3 cubetas de Huevos AA en Calle 45")

        assert result.intent == MessageIntent.nuevo_pedido
        assert len(result.items) == 1
        assert result.items[0].producto == "Huevos AA"
        assert result.items[0].cantidad == 3
        assert result.items[0].unidad == "cubeta"
        assert result.direccion_entrega == "Calle 45 # 12-30"
        assert result.confianza == 0.95

    @pytest.mark.asyncio
    async def test_ambiguous_message_returns_ambiguo_intent(self):
        mock_response = _make_openai_response(AMBIGUOUS_RESPONSE)
        with patch(
            "app.services.interpretation._client.chat.completions.create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await interpret_message("hola quiero algo")

        assert result.intent == MessageIntent.ambiguo
        assert result.items == []
        assert result.razon_ambiguo is not None

    @pytest.mark.asyncio
    async def test_status_query_parsed_correctly(self):
        mock_response = _make_openai_response(STATUS_QUERY_RESPONSE)
        with patch(
            "app.services.interpretation._client.chat.completions.create",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await interpret_message("¿en qué estado va mi pedido?")

        assert result.intent == MessageIntent.consulta_estado
        assert result.confianza >= 0.8

    @pytest.mark.asyncio
    async def test_invalid_openai_response_falls_back_to_ambiguo(self):
        choice = MagicMock()
        choice.message.content = "esto no es json {{{{"
        bad_response = MagicMock()
        bad_response.choices = [choice]

        with patch(
            "app.services.interpretation._client.chat.completions.create",
            new=AsyncMock(return_value=bad_response),
        ):
            result = await interpret_message("algo raro")

        assert result.intent == MessageIntent.ambiguo
        assert result.confianza == 0.0

    @pytest.mark.asyncio
    async def test_context_is_included_in_request(self):
        mock_response = _make_openai_response(VALID_ORDER_RESPONSE)
        create_mock = AsyncMock(return_value=mock_response)

        context = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola! ¿En qué te ayudo?"},
        ]

        with patch(
            "app.services.interpretation._client.chat.completions.create",
            new=create_mock,
        ):
            await interpret_message("3 cubetas", context=context)

        call_args = create_mock.call_args
        messages_sent = call_args.kwargs["messages"]
        roles = [m["role"] for m in messages_sent]
        assert "system" in roles
        assert messages_sent[-1]["content"] == "3 cubetas"


class TestMessageBuilders:
    def test_clarification_message_includes_reason(self):
        msg = build_clarification_message("No especificaste la cantidad.")
        assert "No especificaste la cantidad." in msg

    def test_clarification_message_default_when_no_reason(self):
        msg = build_clarification_message(None)
        assert "producto" in msg.lower() or "cantidad" in msg.lower()

    def test_confirmation_message_lists_items(self):
        from app.schemas.interpretation import InterpretationResult, OrderItemExtracted

        result = InterpretationResult(
            intent=MessageIntent.nuevo_pedido,
            items=[
                OrderItemExtracted(producto="Huevos AA", cantidad=2, unidad="cubeta"),
                OrderItemExtracted(producto="Huevos B", cantidad=1, unidad="cubeta"),
            ],
            confianza=0.9,
        )
        msg = build_confirmation_message(result)
        assert "Huevos AA" in msg
        assert "2" in msg
        assert "Huevos B" in msg

    def test_confirmation_message_includes_address(self):
        from app.schemas.interpretation import InterpretationResult, OrderItemExtracted

        result = InterpretationResult(
            intent=MessageIntent.nuevo_pedido,
            items=[OrderItemExtracted(producto="Huevos AA", cantidad=1, unidad="cubeta")],
            direccion_entrega="Carrera 50 # 20-10",
            confianza=0.9,
        )
        msg = build_confirmation_message(result)
        assert "Carrera 50" in msg
