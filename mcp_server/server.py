"""
MCP Server - Pedidos WhatsApp
==============================
Expone la API de pedidos como herramientas MCP.

Modos de transporte (auto-detectados):
  stdio  -> local, para Claude Desktop / Cursor (sin variable PORT)
  SSE    -> remoto, para deploy en Railway / Fly.io / etc. (PORT definido)

Variables de entorno:
  API_URL        URL base del backend FastAPI
  ADMIN_USERNAME Usuario admin del backend
  ADMIN_PASSWORD Contrasena admin del backend
  MCP_SECRET     (opcional) Token Bearer para proteger el endpoint SSE
  PORT           (Railway lo inyecta automaticamente en modo SSE)
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.parse
from typing import Any

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


# ── DNS cache — resuelve el hostname una sola vez y reutiliza la IP ───────────
# Diagnostico: el DNS es intermitente en este Windows. La unica combinacion
# confiable es getaddrinfo(AF_INET, SOCK_STREAM), pero a veces falla tambien.
# Solucion: resolver UNA sola vez al startup y cachear la IP para siempre.
# Todas las conexiones usan la IP directamente (sin DNS en caliente).
# SSL/TLS sigue usando el hostname original para SNI y verificacion de cert.

import socket as _socket
import ssl as _ssl

_DNS_CACHE: dict[str, str] = {}  # hostname → ip


def _resolve(hostname: str, port: int = 443) -> str:
    """Resuelve hostname a IP probando multiples combinaciones de getaddrinfo."""
    if hostname in _DNS_CACHE:
        return _DNS_CACHE[hostname]

    last_err: Exception | None = None
    for family, socktype in [
        (_socket.AF_INET,   _socket.SOCK_STREAM),
        (_socket.AF_UNSPEC, _socket.SOCK_STREAM),
        (_socket.AF_UNSPEC, 0),
        (_socket.AF_INET,   0),
    ]:
        try:
            results = _socket.getaddrinfo(hostname, port, family, socktype)
            if results:
                ip = results[0][4][0]
                _DNS_CACHE[hostname] = ip
                return ip
        except OSError as e:
            last_err = e

    raise last_err or OSError(f"No se pudo resolver {hostname}")


class _CachedHTTPSConn(http.client.HTTPSConnection):
    """HTTPSConnection que usa IP cacheada para evitar DNS intermitente.

    Resuelve el hostname una vez con la combinacion de flags que funcione,
    conecta directamente a la IP (sin llamar a getaddrinfo en el connect),
    y usa el hostname original para SNI/TLS para que el cert sea valido.
    """

    def connect(self) -> None:
        ip = _resolve(self.host, self.port)

        # Crear socket AF_INET y conectar a la IP — sin llamar a getaddrinfo
        raw = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        timeout = self.timeout
        raw.settimeout(timeout if isinstance(timeout, (int, float)) else 10)
        raw.connect((ip, self.port))

        # SSL con el hostname original para SNI y verificacion del certificado
        ctx: _ssl.SSLContext = getattr(self, "_context", None) or _ssl.create_default_context()
        self.sock = ctx.wrap_socket(raw, server_hostname=self.host)


class _HTTPError(Exception):
    def __init__(self, status: int, body: Any):
        self.status = status
        self.body   = body
        super().__init__(f"HTTP {status}: {body}")


def _do_request(
    method: str,
    url: str,
    *,
    body: dict | None = None,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: int = 10,
) -> tuple[int, Any]:
    """Ejecuta una solicitud HTTPS y devuelve (status_code, json_body)."""
    parsed = urllib.parse.urlparse(url)
    host   = parsed.hostname or ""
    port   = parsed.port or 443
    path   = parsed.path or "/"

    if params:
        clean = {k: str(v) for k, v in params.items() if v is not None}
        if clean:
            path += "?" + urllib.parse.urlencode(clean)

    h: dict[str, str] = {"Accept": "application/json"}
    encoded: bytes | None = None
    if body is not None:
        encoded = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
        h["Content-Length"] = str(len(encoded))
    if headers:
        h.update(headers)

    conn = _CachedHTTPSConn(host, port, timeout=timeout)
    try:
        conn.request(method, path, body=encoded, headers=h)
        resp = conn.getresponse()
        status   = resp.status
        raw_body = resp.read()
    finally:
        conn.close()

    if not raw_body:
        return status, {}
    return status, json.loads(raw_body.decode("utf-8"))


# ── Auth — JWT con refresh automatico en 401 ─────────────────────────────────
_token: str | None = None


def _login() -> str:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError(
            "Faltan credenciales. "
            "Defini ADMIN_USERNAME y ADMIN_PASSWORD en mcp_server/.env o como env vars."
        )
    status, data = _do_request(
        "POST",
        f"{API_URL}/api/v1/auth/login",
        body={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    if status != 200:
        raise _HTTPError(status, data)
    return data["access_token"]


def _get_token() -> str:
    global _token
    if not _token:
        _token = _login()
    return _token


def _auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}"}


# ── HTTP helpers con retry en 401 ─────────────────────────────────────────────
def _get(path: str, **params: Any) -> Any:
    global _token
    status, data = _do_request("GET", f"{API_URL}{path}", headers=_auth_header(), params=params)
    if status == 401:
        _token = None
        status, data = _do_request("GET", f"{API_URL}{path}", headers=_auth_header(), params=params)
    if status >= 400:
        raise _HTTPError(status, data)
    return data


def _patch(path: str, body: dict, **params: Any) -> Any:
    global _token
    status, data = _do_request("PATCH", f"{API_URL}{path}", body=body, headers=_auth_header(), params=params)
    if status == 401:
        _token = None
        status, data = _do_request("PATCH", f"{API_URL}{path}", body=body, headers=_auth_header(), params=params)
    if status >= 400:
        raise _HTTPError(status, data)
    return data


# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "Pedidos WhatsApp",
    instructions=(
        "Servidor MCP para gestionar pedidos del bot de WhatsApp. "
        "Podes listar pedidos, ver detalles, consultar estadisticas, "
        "cambiar estados (con WhatsApp automatico al cliente) y ver pendientes."
    ),
)


@mcp.tool()
def test_conexion() -> dict:
    """Diagnostica la conectividad y estado del cache DNS (debug)."""
    host = "web-production-42788.up.railway.app"
    r: dict = {"dns_cache": dict(_DNS_CACHE)}

    # Probar resolucion con cada combinacion
    for label, family, socktype in [
        ("AF_INET+STREAM",  _socket.AF_INET,   _socket.SOCK_STREAM),
        ("AF_UNSPEC+STREAM",_socket.AF_UNSPEC, _socket.SOCK_STREAM),
        ("AF_UNSPEC+0",     _socket.AF_UNSPEC, 0),
    ]:
        try:
            res = _socket.getaddrinfo(host, 443, family, socktype)
            r[f"getaddrinfo_{label}"] = f"OK: {res[0][4]}"
        except Exception as e:
            r[f"getaddrinfo_{label}"] = f"FAIL: {e}"

    # Probar _resolve (con cache)
    try:
        ip = _resolve(host)
        r["_resolve"] = f"OK: {ip}"
    except Exception as e:
        r["_resolve"] = f"FAIL: {e}"

    # Probar conexion SSL completa con _CachedHTTPSConn
    try:
        conn = _CachedHTTPSConn(host, 443, timeout=5)
        conn.connect()
        conn.close()
        r["CachedHTTPSConn"] = "OK"
    except Exception as e:
        r["CachedHTTPSConn"] = f"FAIL: {e}"

    return r


@mcp.tool()
def listar_pedidos(
    estado: str | None = None,
    telefono: str | None = None,
    limite: int = 20,
) -> list[dict]:
    """Lista pedidos con filtros opcionales.

    Args:
        estado: recibido | confirmado | en_preparacion | listo | entregado | cancelado
        telefono: Numero de WhatsApp del cliente (ej: 573001234567)
        limite: Cuantos devolver (default 20, maximo 200)
    """
    if estado and estado not in VALID_STATUSES:
        return [{"error": f"Estado '{estado}' invalido. Validos: {sorted(VALID_STATUSES)}"}]
    return _get("/api/v1/orders", status=estado, phone=telefono, limit=limite)


@mcp.tool()
def obtener_pedido(order_id: int) -> dict:
    """Obtiene el detalle completo de un pedido por su ID.

    Args:
        order_id: ID numerico del pedido
    """
    try:
        return _get(f"/api/v1/orders/{order_id}")
    except _HTTPError as e:
        if e.status == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        raise


@mcp.tool()
def estadisticas_pedidos() -> dict:
    """Estadisticas de pedidos agrupadas por estado.

    Returns:
        total: conteo general, by_status: conteo por cada estado
    """
    return _get("/api/v1/orders/summary/stats")


@mcp.tool()
def actualizar_estado(
    order_id: int,
    nuevo_estado: str,
    notificar_cliente: bool = True,
) -> dict:
    """Cambia el estado de un pedido. Envia WhatsApp automatico al cliente si notificar_cliente=True.

    Transiciones validas:
        recibido -> confirmado | cancelado
        confirmado -> en_preparacion | cancelado
        en_preparacion -> listo | cancelado
        listo -> entregado
        entregado / cancelado -> (estados finales)

    Args:
        order_id: ID del pedido
        nuevo_estado: Estado destino (ver transiciones validas)
        notificar_cliente: Enviar mensaje WhatsApp al cliente (default True)
    """
    if nuevo_estado not in VALID_STATUSES:
        return {"error": f"Estado '{nuevo_estado}' invalido. Validos: {sorted(VALID_STATUSES)}"}
    try:
        return _patch(
            f"/api/v1/orders/{order_id}/status",
            {"status": nuevo_estado},
            notify=str(notificar_cliente).lower(),
        )
    except _HTTPError as e:
        if e.status == 404:
            return {"error": f"No existe un pedido con ID {order_id}"}
        if e.status == 400:
            detail = e.body.get("detail", "Transicion no permitida") if isinstance(e.body, dict) else str(e.body)
            return {"error": detail}
        raise


@mcp.tool()
def pedidos_pendientes() -> dict:
    """Todos los pedidos que necesitan atencion (no finalizados).

    Agrupa por estado: recibido, confirmado, en_preparacion, listo.
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
        if scope["type"] == "lifespan":
            await app(scope, receive, send)
            return

        hdrs = {k: v for k, v in scope.get("headers", [])}
        auth = hdrs.get(b"authorization", b"").decode()

        if auth == f"Bearer {secret}":
            await app(scope, receive, send)
            return

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
        import uvicorn
        app = mcp.sse_app()
        secret = os.getenv("MCP_SECRET")
        if secret:
            app = _make_secret_guard(app, secret)
        uvicorn.run(app, host="0.0.0.0", port=int(port_env), log_level="info")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
