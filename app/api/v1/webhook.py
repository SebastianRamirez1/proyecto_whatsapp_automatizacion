import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.security import verify_meta_signature
from app.schemas.interpretation import MessageIntent
from app.schemas.webhook import WhatsAppWebhookPayload
from app.services.interpretation import (
    build_clarification_message,
    build_confirmation_message,
    interpret_message,
)
from app.services.whatsapp import send_text_message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = None,
    hub_verify_token: str | None = None,
    hub_challenge: str | None = None,
):
    """Meta calls this endpoint once to verify the webhook URL ownership."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully by Meta.")
        return int(hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


async def _process_message(sender: str, message_body: str, wa_message_id: str) -> None:
    """Background task: interprets the message and replies via WhatsApp."""
    logger.info("Processing message | from=%s | wa_id=%s", sender, wa_message_id)

    result = await interpret_message(message=message_body)

    logger.info(
        "Interpretation | intent=%s | confidence=%.2f | items=%d",
        result.intent,
        result.confianza,
        len(result.items),
    )

    if result.intent == MessageIntent.nuevo_pedido and result.confianza >= 0.6:
        reply = build_confirmation_message(result)
    elif result.intent == MessageIntent.consulta_estado:
        reply = "📦 Estoy consultando el estado de tu pedido, te respondo en un momento."
    elif result.intent == MessageIntent.cancelacion:
        reply = "Recibido. Voy a gestionar la cancelación de tu pedido. Te confirmo en breve."
    elif result.intent == MessageIntent.saludo:
        reply = (
            "¡Hola! Soy el asistente de pedidos. "
            "Para hacer un pedido escríbeme el producto y la cantidad, por ejemplo: "
            "*2 cubetas de huevos AA*"
        )
    else:
        # ambiguo o confianza baja
        reply = build_clarification_message(result.razon_ambiguo)

    try:
        await send_text_message(to=sender, body=reply)
    except Exception as exc:
        logger.error("Failed to send WhatsApp reply | error=%s", exc)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=None),
):
    """Receives and processes incoming WhatsApp events from Meta Cloud API."""
    raw_body = await request.body()

    if not verify_meta_signature(raw_body, x_hub_signature_256 or ""):
        logger.warning("Invalid Meta signature — rejecting webhook.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = WhatsAppWebhookPayload.model_validate_json(raw_body)
    except Exception as exc:
        logger.error("Failed to parse webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    for entry in payload.entry:
        for change in entry.changes:
            if change.field != "messages":
                continue
            for message in change.value.messages or []:
                if message.type != "text" or not message.text:
                    logger.info("Skipping non-text message | type=%s", message.type)
                    continue

                logger.info(
                    "Queuing message for processing | from=%s | body=%r",
                    message.from_,
                    message.text.body[:80],
                )
                background_tasks.add_task(
                    _process_message,
                    sender=message.from_,
                    message_body=message.text.body,
                    wa_message_id=message.id,
                )

    # Meta requiere respuesta 200 inmediata; el procesamiento ocurre en background
    return {"status": "received"}
