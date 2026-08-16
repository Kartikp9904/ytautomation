import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_encryption_cipher() -> Fernet:
    """
    Derive a 32-byte Fernet key deterministically from settings.SECRET_KEY.
    """
    key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    b64_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(b64_key)


def encrypt_token(plain_token: str) -> str:
    """
    Encrypt sensitive OAuth refresh/access tokens at rest.
    """
    if not plain_token:
        return ""
    cipher = _get_encryption_cipher()
    return cipher.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt stored OAuth tokens for API calls.
    """
    if not encrypted_token:
        return ""
    cipher = _get_encryption_cipher()
    return cipher.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


# Aliases for convenience
encrypt_secret = encrypt_token
decrypt_secret = decrypt_token


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
