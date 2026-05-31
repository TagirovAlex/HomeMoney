import bcrypt
import jwt
import time
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config

SECRET_KEY = Config.SECRET_KEY


class TokenBlacklist:
    def __init__(self):
        self._blacklist: dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, token: str, expires_at: float) -> None:
        with self._lock:
            self._blacklist[token] = expires_at

    def is_blacklisted(self, token: str) -> bool:
        with self._lock:
            exp = self._blacklist.get(token)
            if exp is None:
                return False
            if time.time() > exp:
                del self._blacklist[token]
                return False
            return True

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._blacklist.items() if now > v]
            for k in expired:
                del self._blacklist[k]

    def clear(self) -> None:
        with self._lock:
            self._blacklist.clear()


blacklist = TokenBlacklist()

# Автоматическая чистка каждые 5 минут
def _run_cleanup():
    while True:
        time.sleep(300)
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
        if blacklist.is_blacklisted(token):
            return jsonify({"status": "error", "message": "Токен отозван. Выполните вход заново."}), 401
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({"status": "error", "message": "Токен недействителен"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated
