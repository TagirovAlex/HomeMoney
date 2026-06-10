import bcrypt
import hashlib
import jwt
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4
from flask import request, jsonify
from config import Config
from utils.database_session import get_db
from models.database import BlacklistedToken, RefreshToken as RefreshTokenModel

SECRET_KEY = Config.SECRET_KEY


class TokenBlacklist:
    def add(self, jti: str, expires_at: datetime) -> None:
        with get_db() as session:
            existing = session.query(BlacklistedToken).filter(BlacklistedToken.jti == jti).first()
            if not existing:
                session.add(BlacklistedToken(jti=jti, expires_at=expires_at))
                session.commit()

    def is_blacklisted(self, jti: str) -> bool:
        with get_db() as session:
            return session.query(BlacklistedToken).filter(
                BlacklistedToken.jti == jti,
                BlacklistedToken.expires_at > datetime.utcnow(),
            ).first() is not None

    def cleanup(self) -> None:
        with get_db() as session:
            session.query(BlacklistedToken).filter(
                BlacklistedToken.expires_at <= datetime.utcnow()
            ).delete()
            session.commit()

    def clear(self) -> None:
        with get_db() as session:
            session.query(BlacklistedToken).delete()
            session.commit()


blacklist = TokenBlacklist()


def _run_cleanup():
    while True:
        threading.Event().wait(300)
        blacklist.cleanup()


_cleanup_thread = threading.Thread(target=_run_cleanup, daemon=True)
_cleanup_thread.start()


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_token(user_id: int, role: str) -> str:
        payload = {
            "user_id": user_id,
            "role": role,
            "jti": str(uuid4()),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def create_refresh_token(user_id: int, role: str) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
        with get_db() as session:
            session.add(RefreshTokenModel(
                user_id=user_id,
                role=role,
                token_hash=token_hash,
                expires_at=expires_at,
            ))
            session.commit()
        return token

    @staticmethod
    def verify_refresh_token(token: str):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with get_db() as session:
            record = session.query(RefreshTokenModel).filter(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked == False,
                RefreshTokenModel.expires_at > datetime.utcnow(),
            ).first()
            if not record:
                return None
            return {"user_id": record.user_id, "role": record.role, "token_id": record.id}

    @staticmethod
    def revoke_refresh_token(token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with get_db() as session:
            session.query(RefreshTokenModel).filter(
                RefreshTokenModel.token_hash == token_hash
            ).update({"revoked": True})
            session.commit()

    @staticmethod
    def verify_token(token: str):
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


def generate_csrf_token() -> str:
    return secrets.token_hex(32)

def require_csrf(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE"):
            cookie = request.cookies.get("csrf_token")
            header = request.headers.get("X-CSRF-Token")
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                return jsonify({"status": "error", "message": "CSRF-токен недействителен"}), 403
        return f(*args, **kwargs)
    return decorated

def _extract_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("auth_token")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"status": "error", "message": "Требуется авторизация"}), 401
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({"status": "error", "message": "Токен недействителен"}), 401
        if blacklist.is_blacklisted(payload.get("jti", "")):
            return jsonify({"status": "error", "message": "Токен отозван. Выполните вход заново."}), 401
        if request.method in ("POST", "PUT", "DELETE"):
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")
            if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                return jsonify({"status": "error", "message": "CSRF-токен недействителен"}), 403
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated
