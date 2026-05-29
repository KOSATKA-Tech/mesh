import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

logger = logging.getLogger("kosatka_master.auth")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT constants
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    # Use kosatka_api_key as the signing secret for now,
    # or better, a dedicated secret from config.
    encoded_jwt = jwt.encode(to_encode, settings.api_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.api_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
