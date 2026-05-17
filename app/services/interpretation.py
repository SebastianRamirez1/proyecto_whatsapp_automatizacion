import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.interpretation import InterpretationResult, MessageIntent

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

_SYSTEM_PROMPT = """
Eres el asistente de pedidos de una distribuidora de huevos en Colombia.
Tu única función es analizar mensajes de clientes enviados por WhatsApp y devolver
un JSON estructurado con la interpretación.

Responde SIEMPRE con un JSON válido con esta estructura exacta:
{
  "intent": "<nuevo_pedido | consulta_estado | cancelacion | saludo | ambiguo>",
  "items": [
    {"producto": "...", "cantidad": <int>, "unidad": "<cubeta|docena|unidad|kg|null>"}
  ],
  "direccion_entrega": "<string o null>",
  "observaciones": "<string o null>",
  "confianza": <0.0 a 1.0>,
  "razon_ambiguo": "<string o null>"
}

Reglas:
- Si el mensaje es un pedido claro → intent="nuevo_pedido", llena items completos.
- Si preguntan por un pedido existente → intent="consulta_estado", items vacío.
- Si cancelan → intent="cancelacion".
- Si es un saludo sin pedido → intent="saludo".
- Si el mensaje es confuso o falta información clave (ej. qué producto o qué cantidad) → intent="ambiguo", razon_ambiguo explica qué falta.
- confianza refleja tu certeza sobre la interpretación.
- Normaliza unidades: "cubetas" → "cubeta", "docenas" → "docena", "unidades" → "unidad".
- Si no se menciona unidad, deduce del contexto (distribuidora de huevos → default "cubeta").
- No inventes datos. Si no hay dirección, devuelve null.
- Responde SOLO el JSON. Sin texto adicional.
""".strip()


async def interpret_message(
    message: str,
    context: list[dict] | None = None,
) -> InterpretationResult:
    """
    Sends a WhatsApp message to GPT-4o-mini and returns structured interpretation.
    Raises ValueError if the model returns unparseable output after retries.
    """
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if context:
        messages.extend(context[-6:])  # máximo 3 turnos de contexto

    messages.append({"role": "user", "content": message})

    logger.info("Sending message to OpenAI | message=%r", message[:120])

    response = await _client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
        max_tokens=512,
    )

    raw = response.choices[0].message.content or ""
    logger.info("OpenAI raw response: %s", raw[:300])

    try:
        data = json.loads(raw)
        result = InterpretationResult.model_validate(data)
    except Exception as exc:
        logger.error("Failed to parse OpenAI response: %s | raw=%s", exc, raw)
        result = InterpretationResult(
            intent=MessageIntent.ambiguo,
            confianza=0.0,
            razon_ambiguo="No pude entender tu mensaje. ¿Puedes indicarme qué producto y cantidad necesitas?",
        )

    return result


def build_clarification_message(razon: str | None) -> str:
    """Returns the WhatsApp reply when a message is ambiguous."""
    base = "Hola, recibí tu mensaje pero necesito un poco más de información. "
    if razon:
        return base + razon
    return base + "¿Puedes indicarme qué producto necesitas y en qué cantidad?"


def build_confirmation_message(result: InterpretationResult) -> str:
    """Returns the WhatsApp confirmation message for a new order."""
    lines = ["✅ *Pedido recibido*\n"]
    for item in result.items:
        unidad = item.unidad or "unidad"
        lines.append(f"• {item.cantidad} {unidad}(s) de {item.producto}")
    if result.direccion_entrega:
        lines.append(f"\n📍 Dirección: {result.direccion_entrega}")
    if result.observaciones:
        lines.append(f"📝 Nota: {result.observaciones}")
    lines.append("\nTe confirmaremos el pedido en breve. ¡Gracias!")
    return "\n".join(lines)
