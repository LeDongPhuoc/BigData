import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from backend.core.errors import ApiError

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
# Equal-cost work for an unknown email; never persisted or used for a real account.
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))
password_slots = BoundedSemaphore(2)


def hash_password(password):
    if not password_slots.acquire(timeout=2):
        raise ApiError(503, "server_busy", "Authentication busy; try again")
    try:
        return password_hasher.hash(password)
    finally:
        password_slots.release()


def verify_password(encoded, password):
    if not password_slots.acquire(timeout=2):
        raise ApiError(503, "server_busy", "Authentication busy; try again")
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False
    finally:
        password_slots.release()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def token_equal(left, right):
    return hmac.compare_digest(left, right)


def deadline(seconds):
    return (
        (datetime.now(timezone.utc) + timedelta(seconds=seconds))
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def access_token(config, user_key, family_key):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_key,
            "sid": family_key,
            "iss": config.jwt_issuer,
            "aud": config.jwt_audience,
            "iat": now,
            "exp": now + timedelta(seconds=config.access_seconds),
            "jti": secrets.token_hex(16),
        },
        config.jwt_secret,
        algorithm="HS256",
    )


def decode_token(config, token):
    try:
        data = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=["HS256"],
            issuer=config.jwt_issuer,
            audience=config.jwt_audience,
            options={"require": ["sub", "sid", "iss", "aud", "iat", "exp", "jti"]},
        )
        if not isinstance(data["sub"], str) or not isinstance(data["sid"], str):
            raise ValueError("Invalid subject")
        return data
    except (jwt.InvalidTokenError, ValueError) as error:
        raise ApiError(401, "unauthenticated", "Invalid or expired credentials") from error
