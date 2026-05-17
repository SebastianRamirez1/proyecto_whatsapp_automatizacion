from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter()


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Obtener token de acceso",
    description=(
        "Autentica al administrador con usuario y contraseña. "
        "Devuelve un JWT Bearer que debe incluirse en el header `Authorization` "
        "de todos los endpoints protegidos."
    ),
)
def login(body: LoginRequest):
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
