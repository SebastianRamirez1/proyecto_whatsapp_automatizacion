import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings


def verify_meta_signature(payload: bytes, signature: str) -> bool:
    """Validates X-Hub-Signature-256 sent by Meta on every webhook event."""
    expected = hmac.new(
        settings.META_APP_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
