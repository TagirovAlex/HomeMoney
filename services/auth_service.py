import bcrypt
import jwt
import secrets
import threading
import logging
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4
from flask import request, jsonify
from config import Config
from utils.database_session import get_db
from models.database import BlacklistedToken

_log = logging.getLogger(__name__)

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
        token = auth[7:]
        _log.debug("_extract_token from Authorization header")
        return token
    token = request.cookies.get("auth_token")
    _log.debug("_extract_token from cookie: %s", "found" if token else "NOT FOUND")
    return token

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        _log.debug("require_auth method=%s path=%s has_token=%s cookies=%s auth_header=%s",
                    request.method, request.path, bool(token),
                    list(request.cookies.keys()),
                    "Bearer ***" if request.headers.get("Authorization", "").startswith("Bearer ") else "none")
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
