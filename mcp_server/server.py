"""
MCP Server — Pedidos WhatsApp
==============================
Expone la API de pedidos como herramientas MCP para usar en Claude Desktop,
Cursor, o cualquier cliente compatible con el Model Context Protocol.

Inicio rápido:
    pip install -r mcp_server/requirements.txt
    Copiar mcp_server/.env.example → mcp_server/.env y completar credenciales
    python mcp_server/server.py

Luego agregar al claude_desktop_config.json (ver README).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────
# Carga .env si existe (desarrollo local); en producción usa variables de entorno
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

API_URL = os.getenv("API_URL", "https://web-production-42788.up.railway.app").rstrip("/")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Estados válidos y sus transiciones permitidas (espejo de la lógica del backend)
VALID_STATUSES = {
    "recibido",
    "confirmado",
    "en_preparacion",
    "listo",
    "entregado",
    "cancelado",
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
    """Obtiene un JWT nuevo usando las credenciales del entorno."""
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError(
            "Faltan credenciales. "
            "Definí ADMIN_USERNAME y ADMIN_PASSWORD en mcp_server/.env"
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
    clean_params = {k: v for k, v in params.items() if v is not None}
    resp = httpx.get(f"{API_URL}{path}", headers=_auth_headers(), params=clean_params, timeout=10)
    if resp.status_code == 401:
        _token = None  # token expirado → forzar re-login
        resp = httpx.get(f"{API_URL}{path}", headers=_auth_headers(), params=clean_params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, body: dict) -> Any:
    global _token
    resp = httpx.patch(f"{API_URL}{path}", headers=_auth_headers(), json=body, timeout=10)
    if resp.status_code == 401:
        _token = None
        resp = httpx.patch(f"{API_URL}{path}", headers=_auth_headers(), json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "Pedidos WhatsApp",
    instructions=(
        "Servidor MCP para gestionar pedidos del bot de WhatsApp. "
        "Podés listar pedidos, ver el detalle de uno, consultar estadísticas, "
        "actualizar el estado de un pedido (con notificación automática al cliente "
        "por WhatsApp) y cancelar pedidos."
    ),
)


# ── Tool 1: listar_pedidos ────────────────────────────────────────────────────
@mcp.tool()
def listar_pedidos(
    estado: str | None = None,
    telefono: str | None = None,
    limite: int = 20,
) -> list[dict]:
    """Lista pedidos del sistema con filtros opcionales.

    Args:
        estado: Filtrar por estado del pedido. Valores válidos:
                recibido | confirmado | en_preparacion | listo | entregado | cancelado
        telefono: Filtrar por número de WhatsApp del cliente (ej: 573001234567)
        limite: Cuántos pedidos devolver (default 20, máximo 200)

    Returns:
        Lista de pedidos con id, cliente, items, estado, dirección y fechas.
    """
    if estado and estado not in VALID_STATUSES:
        return [{"error": f"Estado '{estado}' inválido. Válidos: {sorted(VALID_STATUSES)}"}]
    return _get("/api/v1/orders", status=estado, phone=telefono, limit=limite)


# ── Tool 2: obtener_pedido ────────────────────────────────────────────────────
@mcp.tool()
def obtener_pedido(order_id: int) -> dict:
    """Obtiene el detalle completo de un pedido por su ID.

    Args:
        order_id: ID numérico del pedido (visible en la lista de pedidos)

    Returns:
        Pedido con cliente, lista de items con cantidades, dirección de entrega,
        mensaje original de WhatsApp, estado actual y timestamps.
    """
    try:
        return _get(f"/api/v1/orders/{order_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        raise


# ── Tool 3: estadisticas_pedidos ─────────────────────────────────────────────
@mcp.tool()
def estadisticas_pedidos() -> dict:
    """Devuelve estadísticas de pedidos agrupadas por estado.

    Returns:
        Objeto con:
        - total: cantidad total de pedidos en el sistema
        - by_status: conteo de pedidos por cada estado posible
    """
    return _get("/api/v1/orders/summary/stats")


# ── Tool 4: actualizar_estado ─────────────────────────────────────────────────
@mcp.tool()
def actualizar_estado(
    order_id: int,
    nuevo_estado: str,
    notificar_cliente: bool = True,
) -> dict:
    """Cambia el estado de un pedido siguiendo la máquina de estados del negocio.

    Al cambiar el estado, el cliente recibe automáticamente un mensaje de
    WhatsApp con la actualización (salvo que notificar_cliente=False).

    Transiciones válidas:
        recibido       → confirmado | cancelado
        confirmado     → en_preparacion | cancelado
        en_preparacion → listo | cancelado
        listo          → entregado
        entregado      → (estado final, sin transiciones)
        cancelado      → (estado final, sin transiciones)

    Args:
        order_id: ID numérico del pedido
        nuevo_estado: Estado destino (ver transiciones válidas arriba)
        notificar_cliente: Si True, envía WhatsApp automático al cliente (default True)

    Returns:
        El pedido actualizado con el nuevo estado y timestamps.
    """
    if nuevo_estado not in VALID_STATUSES:
        return {"error": f"Estado '{nuevo_estado}' inválido. Válidos: {sorted(VALID_STATUSES)}"}

    try:
        return _patch(
            f"/api/v1/orders/{order_id}/status?notify={str(notificar_cliente).lower()}",
            {"status": nuevo_estado},
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        if e.response.status_code == 400:
            detail = e.response.json().get("detail", "Transición de estado no permitida")
            return {"error": detail}
        raise


# ── Tool 5: pedidos_pendientes ─────────────────────────────────────────────────
@mcp.tool()
def pedidos_pendientes() -> dict:
    """Devuelve todos los pedidos que requieren atención inmediata.

    Un pedido "pendiente" es cualquiera que no está en estado final
    (entregado o cancelado): recibido, confirmado, en_preparacion, listo.

    Returns:
        Objeto con conteo total y listas separadas por estado, ordenadas
        por fecha de creación para identificar los más urgentes.
    """
    activos = [
        p for p in _get("/api/v1/orders", limit=200)
        if p["status"] not in ("entregado", "cancelado")
    ]

    por_estado: dict[str, list] = {
        "recibido": [],
        "confirmado": [],
        "en_preparacion": [],
        "listo": [],
    }
    for pedido in activos:
        estado = pedido["status"]
        if estado in por_estado:
            por_estado[estado].append(pedido)

    return {
        "total_pendientes": len(activos),
        "por_estado": {k: v for k, v in por_estado.items() if v},
    }


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
