"""
MCP Server — Pedidos WhatsApp
==============================
Expone la API de pedidos como herramientas MCP.

Modos de transporte (auto-detectados):
  stdio  → local, para Claude Desktop / Cursor (sin variable PORT)
  SSE    → remoto, para deploy en Railway / Fly.io / etc. (PORT definido)

Variables de entorno:
  API_URL        URL base del backend FastAPI
  ADMIN_USERNAME Usuario admin del backend
  ADMIN_PASSWORD Contraseña admin del backend
  MCP_SECRET     (opcional) Token Bearer para proteger el endpoint SSE
  PORT           (Railway lo inyecta automáticamente en modo SSE)
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

API_URL        = os.getenv("API_URL", "https://web-production-42788.up.railway.app").rstrip("/")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

VALID_STATUSES = {
    "recibido", "confirmado", "en_preparacion",
    "listo", "entregado", "cancelado",
}

VALID_TRANSITIONS: dict[str, list[str]] = {
    "recibido":       ["confirmado", "cancelado"],
    "confirmado":     ["en_preparacion", "cancelado"],
    "en_preparacion": ["listo", "cancelado"],
    "listo":          ["entregado"],
    "entregado":      [],
    "cancelado":      [],
}

# ── Auth — JWT con refresh automático en 401 ─────────────────────────────────
_token: str | None = None


def _login() -> str:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError(
            "Faltan credenciales. "
            "Definí ADMIN_USERNAME y ADMIN_PASSWORD en mcp_server/.env o como env vars."
        )
    resp = httpx.post(
        f"{API_URL}/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_token() -> str:
    global _token
    if not _token:
        _token = _login()
    return _token


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}"}


# ── HTTP helpers con retry en 401 ─────────────────────────────────────────────
def _get(path: str, **params: Any) -> Any:
    global _token
    clean = {k: v for k, v in params.items() if v is not None}
    resp = httpx.get(f"{API_URL}{path}", headers=_auth_headers(), params=clean, timeout=10)
    if resp.status_code == 401:
        _token = None
        resp = httpx.get(f"{API_URL}{path}", headers=_auth_headers(), params=clean, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, body: dict, **params: Any) -> Any:
    global _token
    clean = {k: v for k, v in params.items() if v is not None}
    resp = httpx.patch(f"{API_URL}{path}", headers=_auth_headers(), json=body, params=clean, timeout=10)
    if resp.status_code == 401:
        _token = None
        resp = httpx.patch(f"{API_URL}{path}", headers=_auth_headers(), json=body, params=clean, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "Pedidos WhatsApp",
    instructions=(
        "Servidor MCP para gestionar pedidos del bot de WhatsApp. "
        "Podés listar pedidos, ver detalles, consultar estadísticas, "
        "cambiar estados (con WhatsApp automático al cliente) y ver pendientes."
    ),
)


@mcp.tool()
def listar_pedidos(
    estado: str | None = None,
    telefono: str | None = None,
    limite: int = 20,
) -> list[dict]:
    """Lista pedidos con filtros opcionales.

    Args:
        estado: recibido | confirmado | en_preparacion | listo | entregado | cancelado
        telefono: Número de WhatsApp del cliente (ej: 573001234567)
        limite: Cuántos devolver (default 20, máximo 200)
    """
    if estado and estado not in VALID_STATUSES:
        return [{"error": f"Estado '{estado}' inválido. Válidos: {sorted(VALID_STATUSES)}"}]
    return _get("/api/v1/orders", status=estado, phone=telefono, limit=limite)


@mcp.tool()
def obtener_pedido(order_id: int) -> dict:
    """Obtiene el detalle completo de un pedido por su ID.

    Args:
        order_id: ID numérico del pedido
    """
    try:
        return _get(f"/api/v1/orders/{order_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        raise


@mcp.tool()
def estadisticas_pedidos() -> dict:
    """Estadísticas de pedidos agrupadas por estado.

    Returns:
        total: conteo general · by_status: conteo por cada estado
    """
    return _get("/api/v1/orders/summary/stats")


@mcp.tool()
def actualizar_estado(
    order_id: int,
    nuevo_estado: str,
    notificar_cliente: bool = True,
) -> dict:
    """Cambia el estado de un pedido. Envía WhatsApp automático al cliente si notificar_cliente=True.

    Transiciones válidas:
        recibido → confirmado | cancelado
        confirmado → en_preparacion | cancelado
        en_preparacion → listo | cancelado
        listo → entregado
        entregado / cancelado → (estados finales)

    Args:
        order_id: ID del pedido
        nuevo_estado: Estado destino (ver transiciones válidas)
        notificar_cliente: Enviar mensaje WhatsApp al cliente (default True)
    """
    if nuevo_estado not in VALID_STATUSES:
        return {"error": f"Estado '{nuevo_estado}' inválido. Válidos: {sorted(VALID_STATUSES)}"}
    try:
        return _patch(
            f"/api/v1/orders/{order_id}/status",
            {"status": nuevo_estado},
            notify=str(notificar_cliente).lower(),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        if e.response.status_code == 400:
            return {"error": e.response.json().get("detail", "Transición no permitida")}
        raise


@mcp.tool()
def pedidos_pendientes() -> dict:
    """Todos los pedidos que necesitan atención (no finalizados).

    Agrupa por estado: recibido, confirmado, en_preparacion, listo.
    Útil para ver de un vistazo qué hay que atender.
    """
    activos = [
        p for p in _get("/api/v1/orders", limit=200)
        if p["status"] not in ("entregado", "cancelado")
    ]
    por_estado: dict[str, list] = {
        "recibido": [], "confirmado": [],
        "en_preparacion": [], "listo": [],
    }
    for pedido in activos:
        if pedido["status"] in por_estado:
            por_estado[pedido["status"]].append(pedido)

    return {
        "total_pendientes": len(activos),
        "por_estado": {k: v for k, v in por_estado.items() if v},
    }


# ── ASGI guard para modo SSE ──────────────────────────────────────────────────
def _make_secret_guard(app: Any, secret: str) -> Any:
    """Middleware ASGI liviano que rechaza requests sin el Bearer token correcto."""
    async def guarded(scope: dict, receive: Any, send: Any) -> None:
        # Dejar pasar eventos de ciclo de vida del servidor
        if scope["type"] == "lifespan":
            await app(scope, receive, send)
            return

        headers = {k: v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode()

        if auth == f"Bearer {secret}":
            await app(scope, receive, send)
            return

        # Rechazar con 401
        body = b'{"error":"Unauthorized - falta o es incorrecto el Bearer token"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body, "more_body": False})

    return guarded


# ── Entrypoint ────────────────────────────────────────────────────────────────
def main() -> None:
    port_env = os.getenv("PORT")

    if port_env:
        # ── Modo SSE: deploy en Railway / Fly.io / cualquier PaaS ────────────
        import uvicorn

        app = mcp.sse_app()

        secret = os.getenv("MCP_SECRET")
        if secret:
            app = _make_secret_guard(app, secret)
            print(f"[MCP] SSE mode — puerto {port_env} — auth: Bearer ****")
        else:
            print(f"[MCP] SSE mode — puerto {port_env} — auth: deshabilitada")

        uvicorn.run(app, host="0.0.0.0", port=int(port_env), log_level="info")
    else:
        # ── Modo stdio: Claude Desktop / Cursor local ─────────────────────────
        mcp.run()


if __name__ == "__main__":
    main()
