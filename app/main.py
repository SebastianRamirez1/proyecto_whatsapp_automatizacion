import logging

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1 import auth, orders, webhook
from app.core.config import settings
from app.core.security import get_current_user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    description=(
        "## Sistema de Automatización de Pedidos por WhatsApp\n\n"
        "Recibe mensajes de clientes via WhatsApp Business API, los interpreta con "
        "**OpenAI GPT-4o-mini**, registra los pedidos en PostgreSQL y confirma "
        "automáticamente al cliente.\n\n"
        "### Flujo\n"
        "1. Cliente envía mensaje → **Webhook** lo recibe\n"
        "2. **Motor IA** clasifica la intención y extrae los campos del pedido\n"
        "3. **Gestor de pedidos** escribe en base de datos\n"
        "4. El bot confirma al cliente con el N° de pedido\n"
        "5. El **admin** avanza el estado → el cliente recibe notificación automática\n\n"
        "### Autenticación\n"
        "Los endpoints de administración requieren un **JWT Bearer**. "
        "Obtenerlo via `POST /api/v1/auth/login`."
    ),
    contact={
        "name": "Sebastián Ramírez",
        "email": "sebastianacevedo123.sra@gmail.com",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(webhook.router, prefix="/api/v1", tags=["Webhook"])
app.include_router(orders.router, prefix="/api/v1", tags=["Orders (Admin)"])


@app.get("/health", tags=["Health"], summary="Health check")
def health_check():
    """Returns service status and current version."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.post("/debug/whatsapp-test", tags=["Health"], summary="Test envío WhatsApp")
async def debug_whatsapp(to: str, _: str = Depends(get_current_user)):
    """Prueba el envío de WhatsApp con el token actual del servidor. Solo admin."""
    import os
    os_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "NO_ENCONTRADO_EN_OS_ENV")
    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": "🔧 Test de diagnóstico — el token del servidor funciona."},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=payload)
    return {
        "status_code": resp.status_code,
        "token_from_settings": settings.WHATSAPP_ACCESS_TOKEN[:20] + "...",
        "token_from_os_env": os_token[:20] + "...",
        "response": resp.json(),
    }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
