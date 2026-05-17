from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: WhatsAppTextBody | None = None


class WhatsAppContact(BaseModel):
    profile: dict[str, Any]
    wa_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: dict[str, Any]
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppMessage] | None = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]
