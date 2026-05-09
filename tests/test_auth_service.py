import pytest
from services.auth_service import AuthService

class TestAuthService:
    def test_hash_and_verify_password(self):
        pw = "test_password_123"
        hashed = AuthService.hash_password(pw)
        assert hashed != pw
        assert AuthService.verify_password(pw, hashed) is True
        assert AuthService.verify_password("wrong", hashed) is False

    def test_create_and_verify_token(self):
        token = AuthService.create_token(1, "Admin")
        assert token is not None
        payload = AuthService.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["role"] == "Admin"

    def test_verify_invalid_token(self):
        payload = AuthService.verify_token("invalid_token_here")
        assert payload is None

    def test_create_token_user_role(self):
        token = AuthService.create_token(42, "User")
        payload = AuthService.verify_token(token)
        assert payload["user_id"] == 42
        assert payload["role"] == "User"
