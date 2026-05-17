import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WA_API_URL = (
    f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
)
_HEADERS = {
    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


async def send_text_message(to: str, body: str) -> dict:
    """
    Sends a plain-text WhatsApp message via Meta Cloud API.
    `to` must be in international format without '+' (e.g. '573001234567').
    """
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_WA_API_URL, headers=_HEADERS, json=payload)

    if response.status_code != 200:
        logger.error(
            "WhatsApp API error | status=%s | body=%s",
            response.status_code,
            response.text[:300],
        )
        response.raise_for_status()

    data = response.json()
    logger.info("Message sent | to=%s | wa_id=%s", to, data.get("messages", [{}])[0].get("id"))
    return data
