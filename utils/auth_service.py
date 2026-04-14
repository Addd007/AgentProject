from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.database import SQLALCHEMY_DATABASE_URL

Base = declarative_base()

AUTH_COOKIE_NAME = "agentproject_auth"
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(60 * 60 * 2)))# 默认 2 小时 
AUTH_SECRET = os.getenv("AUTH_SECRET")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"

if not AUTH_SECRET:
    raise RuntimeError("AUTH_SECRET environment variable is required")
if len(AUTH_SECRET) < 32:
    raise RuntimeError("AUTH_SECRET must be at least 32 characters long")


class UserRecord(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    username: str


class AuthService:
    def __init__(self, db_url: str = SQLALCHEMY_DATABASE_URL):
        self.engine = create_engine(db_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def register_user(self, username: str, password: str) -> AuthUser:
        normalized_username = username.strip().lower()
        self._validate_credentials(normalized_username, password)

        with self.SessionLocal() as db:
            existing = db.query(UserRecord).filter(UserRecord.username == normalized_username).first()
            if existing:
                raise ValueError("用户名已存在")

            user = UserRecord(
                user_id=secrets.token_hex(16),
                username=normalized_username,
                password_hash=self._hash_password(password),
            )
            db.add(user)
            db.commit()
            return AuthUser(user_id=user.user_id, username=user.username)

    def authenticate_user(self, username: str, password: str) -> AuthUser | None:
        normalized_username = username.strip().lower()
        with self.SessionLocal() as db:
            user = db.query(UserRecord).filter(UserRecord.username == normalized_username).first()
            if not user:
                return None
            if not self._verify_password(password, user.password_hash):
                return None
            return AuthUser(user_id=user.user_id, username=user.username)

    def get_user_by_id(self, user_id: str) -> AuthUser | None:
        with self.SessionLocal() as db:
            user = db.query(UserRecord).filter(UserRecord.user_id == user_id).first()
            if not user:
                return None
            return AuthUser(user_id=user.user_id, username=user.username)

    def create_token(self, user: AuthUser) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "exp": int((now + timedelta(seconds=AUTH_TOKEN_TTL_SECONDS)).timestamp()),
            "iat": int(now.timestamp()),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = self._b64encode(payload_bytes)
        signature = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{self._b64encode(signature)}"

    def verify_token(self, token: str) -> AuthUser | None:
        try:
            payload_b64, signature_b64 = token.split(".", 1)
        except ValueError:
            return None

        expected_sig = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()

        actual_sig = self._b64decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(self._b64decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None

        user = self.get_user_by_id(str(payload.get("sub", "")))
        if not user:
            return None
        return user

    def _validate_credentials(self, username: str, password: str) -> None:
        if len(username) < 3 or len(username) > 32:
            raise ValueError("用户名长度需在 3 到 32 位之间")
        if not username.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名仅支持字母、数字、下划线和中划线")
        if len(password) < 8 or len(password) > 128:
            raise ValueError("密码长度需在 8 到 128 位之间")

    def _hash_password(self, password: str) -> str:
        iterations = 310000
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return "$".join([
            "pbkdf2_sha256",
            str(iterations),
            self._b64encode(salt),
            self._b64encode(digest),
        ])

    def _verify_password(self, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, iterations_str, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        salt = self._b64decode(salt_b64)
        expected = self._b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations_str),
        )
        return hmac.compare_digest(actual, expected)

    def _b64encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    def _b64decode(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))