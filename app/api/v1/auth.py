import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter()

# ── Simple in-memory rate limiter ─────────────────────────────────────────────
# Allows MAX_ATTEMPTS per IP within WINDOW_SECONDS.
# No external dependency required; resets on restart (acceptable for single-instance).
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60
_login_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    with _lock:
        attempts = _login_attempts[ip]
        # Remove attempts outside the sliding window
        _login_attempts[ip] = [t for t in attempts if now - t < _WINDOW_SECONDS]
        if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos. Espera {_WINDOW_SECONDS} segundos.",
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )
        _login_attempts[ip].append(now)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Obtener token de acceso",
    description=(
        "Autentica al administrador con usuario y contraseña. "
        "Devuelve un JWT Bearer que debe incluirse en el header `Authorization` "
        "de todos los endpoints protegidos. "
        "Máximo 5 intentos por IP cada 60 segundos."
    ),
)
def login(body: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if body.username != settings.ADMIN_USERNAME or not verify_password(
        body.password, settings.ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
