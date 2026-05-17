import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.security import verify_meta_signature
from app.schemas.webhook import WhatsAppWebhookPayload

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


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
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
                logger.info(
                    "Incoming message | from=%s | id=%s | type=%s | body=%s",
                    message.from_,
                    message.id,
                    message.type,
                    message.text.body if message.text else "<no-text>",
                )

    return {"status": "received"}
