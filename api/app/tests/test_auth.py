from datetime import timedelta
from unittest.mock import MagicMock, patch

from app.auth.auth import (
    add_token_to_denylist,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    get_random_password,
    get_scopes_for_user,
    is_token_revoked,
    verify_password,
)
from app.auth.utils import role_has_scope


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = get_password_hash("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_wrong_password(self):
        hashed = get_password_hash("mysecret")
        assert verify_password("wrongpassword", hashed) is False


class TestCreateAccessToken:
    def test_with_expires_delta(self):
        token = create_access_token({"sub": "user@test.com"}, timedelta(minutes=30))
        assert isinstance(token, str)
        assert len(token) > 0

    def test_without_expires_delta_uses_default(self):
        token = create_access_token({"sub": "user@test.com"})
        assert isinstance(token, str)
        assert len(token) > 0


class TestCreateRefreshToken:
    def test_with_expires_delta(self):
        token = create_refresh_token({"sub": "user@test.com"}, timedelta(days=1))
        assert isinstance(token, str)
        assert len(token) > 0

    def test_without_expires_delta_uses_default(self):
        token = create_refresh_token({"sub": "user@test.com"})
        assert isinstance(token, str)
        assert len(token) > 0


class TestTokenDenylist:
    def test_is_token_not_revoked(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        with patch("app.auth.auth.get_redis_client", return_value=mock_redis):
            result = is_token_revoked({"jti": "test-jti-123"})
        assert result is False
        mock_redis.get.assert_called_once_with("auth:jwt_denylist:test-jti-123")

    def test_is_token_revoked(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "revoked"
        with patch("app.auth.auth.get_redis_client", return_value=mock_redis):
            result = is_token_revoked({"jti": "test-jti-123"})
        assert result is True

    def test_add_token_to_denylist(self):
        mock_redis = MagicMock()
        with patch("app.auth.auth.get_redis_client", return_value=mock_redis):
            add_token_to_denylist("test-jti-456")
        mock_redis.set.assert_called_once_with("auth:jwt_denylist:test-jti-456", "revoked")


class TestAuthenticateUser:
    def test_user_not_found_returns_false(self):
        mock_db = MagicMock()
        with patch("app.auth.auth.users_repository.get_user_by_email", return_value=None):
            result = authenticate_user(mock_db, "notfound@test.com", "password")
        assert result is False

    def test_wrong_password_returns_false(self):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.hashed_password = get_password_hash("correctpassword")
        with patch("app.auth.auth.users_repository.get_user_by_email", return_value=mock_user):
            result = authenticate_user(mock_db, "user@test.com", "wrongpassword")
        assert result is False

    def test_correct_credentials_returns_user(self):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.hashed_password = get_password_hash("correctpassword")
        with patch("app.auth.auth.users_repository.get_user_by_email", return_value=mock_user):
            result = authenticate_user(mock_db, "user@test.com", "correctpassword")
        assert result == mock_user


class TestRoleHasScope:
    def test_wildcard_grants_everything(self):
        assert role_has_scope(["*"], "events:create") is True
        assert role_has_scope(["*"], "anything:here") is True

    def test_resource_wildcard_grants_resource_scopes(self):
        assert role_has_scope(["events:*"], "events:create") is True
        assert role_has_scope(["events:*"], "events:delete") is True
        assert role_has_scope(["events:*"], "attributes:create") is False

    def test_exact_scope_match(self):
        assert role_has_scope(["events:create"], "events:create") is True
        assert role_has_scope(["events:create"], "events:delete") is False

    def test_empty_scopes_returns_false(self):
        assert role_has_scope([], "events:create") is False


class TestGetScopesForUser:
    def test_returns_role_scopes(self):
        user = MagicMock()
        user.role.scopes = ["events:read", "events:create"]
        scopes = get_scopes_for_user(user)
        assert scopes == ["events:read", "events:create"]

    def test_returns_wildcard_for_admin(self):
        user = MagicMock()
        user.role.scopes = ["*"]
        scopes = get_scopes_for_user(user)
        assert scopes == ["*"]

    def test_returns_empty_for_no_scopes(self):
        user = MagicMock()
        user.role.scopes = []
        scopes = get_scopes_for_user(user)
        assert scopes == []


class TestGetRandomPassword:
    def test_returns_string_of_length_16(self):
        pwd = get_random_password()
        assert isinstance(pwd, str)
        assert len(pwd) == 16

    def test_passwords_differ_across_calls(self):
        passwords = {get_random_password() for _ in range(10)}
        assert len(passwords) > 1
