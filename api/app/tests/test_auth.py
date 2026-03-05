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


class TestGetScopesForUser:
    def _make_user(self, **role_kwargs):
        role = MagicMock()
        role.perm_full = False
        role.perm_admin = False
        role.perm_auth = False
        role.perm_add = False
        role.perm_modify = False
        role.perm_modify_org = False
        role.perm_publish = False
        role.perm_delegate = False
        role.perm_sync = False
        role.perm_audit = False
        role.perm_site_admin = False
        role.perm_regexp_access = False
        role.perm_tagger = False
        role.perm_template = False
        role.perm_sharing_group = False
        role.perm_tag_editor = False
        role.perm_sighting = False
        role.perm_object_template = False
        role.perm_galaxy_editor = False
        role.perm_warninglist = False
        role.perm_publish_zmq = False
        role.perm_publish_kafka = False
        role.perm_decaying = False
        for key, value in role_kwargs.items():
            setattr(role, key, value)
        user = MagicMock()
        user.role = role
        return user

    def test_perm_full_returns_wildcard(self):
        user = self._make_user(perm_full=True)
        scopes = get_scopes_for_user(user)
        assert scopes == ["*"]

    def test_perm_admin_grants_admin_scopes(self):
        user = self._make_user(perm_admin=True)
        scopes = get_scopes_for_user(user)
        assert "users:*" in scopes
        assert "events:*" in scopes
        assert "attributes:*" in scopes
        assert "galaxies:*" in scopes
        assert "feeds:*" in scopes
        assert "correlations:*" in scopes

    def test_perm_auth_grants_auth_login(self):
        user = self._make_user(perm_auth=True)
        scopes = get_scopes_for_user(user)
        assert "auth:login" in scopes

    def test_perm_add_grants_create_scopes(self):
        user = self._make_user(perm_add=True)
        scopes = get_scopes_for_user(user)
        assert "events:create" in scopes
        assert "attributes:create" in scopes
        assert "objects:create" in scopes
        assert "tags:create" in scopes

    def test_perm_modify_grants_update_scopes(self):
        user = self._make_user(perm_modify=True)
        scopes = get_scopes_for_user(user)
        assert "events:update" in scopes
        assert "attributes:update" in scopes
        assert "objects:update" in scopes
        assert "tags:update" in scopes

    def test_no_perms_returns_empty_list(self):
        user = self._make_user()
        scopes = get_scopes_for_user(user)
        assert scopes == []

    def test_multiple_perms_combined(self):
        user = self._make_user(perm_add=True, perm_modify=True, perm_auth=True)
        scopes = get_scopes_for_user(user)
        assert "events:create" in scopes
        assert "events:update" in scopes
        assert "auth:login" in scopes


class TestGetRandomPassword:
    def test_returns_string_of_length_12(self):
        pwd = get_random_password()
        assert isinstance(pwd, str)
        assert len(pwd) == 12

    def test_passwords_differ_across_calls(self):
        passwords = {get_random_password() for _ in range(10)}
        assert len(passwords) > 1
