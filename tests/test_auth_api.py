import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()
pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
CHANGE_PASSWORD = "/api/v1/auth/change-password/"


def registration_payload(**overrides) -> dict:
    data = {
        "email": "new.user@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": "Very-Secure-Pass-91",
        "password_confirm": "Very-Secure-Pass-91",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------- registration
class TestRegistration:
    def test_successful_registration(self, api_client):
        response = api_client.post(REGISTER, registration_payload())

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "new.user@example.com"
        assert "password" not in body and "password_confirm" not in body
        assert User.objects.filter(email="new.user@example.com").exists()

    def test_email_is_stored_lowercase(self, api_client):
        api_client.post(REGISTER, registration_payload(email="Mixed.Case@Example.com"))

        assert User.objects.filter(email="mixed.case@example.com").exists()

    def test_duplicate_email_rejected(self, api_client, user):
        response = api_client.post(REGISTER, registration_payload(email=user.email))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.json()

    def test_duplicate_email_rejected_case_insensitively(self, api_client, user):
        response = api_client.post(REGISTER, registration_payload(email="ALICE@example.com"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.json()

    def test_password_mismatch_rejected(self, api_client):
        response = api_client.post(REGISTER, registration_payload(password_confirm="Different-Pass-91"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.json()

    @pytest.mark.parametrize("weak", ["short", "password123", "12345678901"])
    def test_weak_passwords_rejected(self, api_client, weak):
        response = api_client.post(REGISTER, registration_payload(password=weak, password_confirm=weak))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()

    def test_missing_fields_rejected(self, api_client):
        response = api_client.post(REGISTER, {"email": "x@example.com"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert {"password", "first_name", "last_name"} <= set(response.json())

    def test_cannot_register_as_staff(self, api_client):
        api_client.post(REGISTER, registration_payload(is_staff=True, is_superuser=True))

        user = User.objects.get(email="new.user@example.com")
        assert not user.is_staff and not user.is_superuser


# ---------------------------------------------------------------- login / tokens
class TestTokens:
    def test_login_returns_access_and_refresh(self, api_client, user, password):
        response = api_client.post(LOGIN, {"email": user.email, "password": password})

        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= set(response.json())

    def test_login_is_case_insensitive_for_email(self, api_client, user, password):
        response = api_client.post(LOGIN, {"email": "ALICE@EXAMPLE.COM", "password": password})

        assert response.status_code == status.HTTP_200_OK

    def test_wrong_password_rejected(self, api_client, user):
        response = api_client.post(LOGIN, {"email": user.email, "password": "wrong-password"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unknown_email_gives_same_error_as_wrong_password(self, api_client, user):
        wrong_pw = api_client.post(LOGIN, {"email": user.email, "password": "wrong"})
        no_user = api_client.post(LOGIN, {"email": "nobody@example.com", "password": "wrong"})

        # Identical responses: an attacker can't use login to discover which emails exist.
        assert wrong_pw.status_code == no_user.status_code == status.HTTP_401_UNAUTHORIZED
        assert wrong_pw.json() == no_user.json()

    def test_inactive_user_cannot_log_in(self, api_client, user, password):
        user.is_active = False
        user.save()

        response = api_client.post(LOGIN, {"email": user.email, "password": password})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_returns_new_tokens_and_rotates(self, api_client, user, tokens_for):
        old_refresh = tokens_for(user)["refresh"]

        response = api_client.post(REFRESH, {"refresh": old_refresh})
        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= set(response.json())

        # Rotation: the old refresh token was blacklisted and can't be reused.
        reuse = api_client.post(REFRESH, {"refresh": old_refresh})
        assert reuse.status_code == status.HTTP_401_UNAUTHORIZED

    def test_garbage_refresh_token_rejected(self, api_client):
        response = api_client.post(REFRESH, {"refresh": "not-a-token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_is_rate_limited(self, api_client, user, monkeypatch):
        # DRF reads throttle rates once at import time, so for this test we
        # temporarily lower the "auth" limit to 3 requests per minute.
        from rest_framework.throttling import ScopedRateThrottle

        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "3/minute"})

        codes = [
            api_client.post(LOGIN, {"email": user.email, "password": "wrong"}).status_code
            for _ in range(4)
        ]

        assert codes[:3] == [401, 401, 401]
        assert codes[3] == status.HTTP_429_TOO_MANY_REQUESTS


# ---------------------------------------------------------------- me
class TestMe:
    def test_requires_authentication(self, api_client):
        response = api_client.get(ME)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_access_token_rejected(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        response = api_client.get(ME)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_current_user(self, auth_client, user):
        response = auth_client.get(ME)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["email"] == user.email
        assert body["full_name"] == "Alice Khan"
        assert "password" not in body

    def test_patch_updates_names(self, auth_client, user):
        response = auth_client.patch(ME, {"first_name": "Alicia"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["first_name"] == "Alicia"
        user.refresh_from_db()
        assert user.first_name == "Alicia"

    def test_patch_ignores_protected_fields(self, auth_client, user):
        auth_client.patch(ME, {"email": "hacker@example.com", "is_staff": True, "is_superuser": True})

        user.refresh_from_db()
        assert user.email == "alice@example.com"
        assert not user.is_staff and not user.is_superuser

    def test_blank_name_rejected(self, auth_client):
        response = auth_client.patch(ME, {"first_name": ""})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_put_not_allowed(self, auth_client):
        response = auth_client.put(ME, {"first_name": "A", "last_name": "B"})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------- change password
class TestChangePassword:
    def payload(self, old, new="Brand-New-Secret-77"):
        return {"old_password": old, "new_password": new, "new_password_confirm": new}

    def test_requires_authentication(self, api_client, password):
        response = api_client.post(CHANGE_PASSWORD, self.payload(password))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_old_password_rejected(self, auth_client):
        response = auth_client.post(CHANGE_PASSWORD, self.payload("not-my-password"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "old_password" in response.json()

    def test_weak_new_password_rejected(self, auth_client, password):
        response = auth_client.post(CHANGE_PASSWORD, self.payload(password, new="123"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in response.json()

    def test_same_password_rejected(self, auth_client, password):
        response = auth_client.post(CHANGE_PASSWORD, self.payload(password, new=password))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_success_changes_password_and_revokes_sessions(self, api_client, user, password, tokens_for):
        tokens = tokens_for(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = api_client.post(CHANGE_PASSWORD, self.payload(password))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        api_client.credentials()  # drop the header
        # Old password no longer works, new one does.
        assert api_client.post(LOGIN, {"email": user.email, "password": password}).status_code == 401
        assert api_client.post(
            LOGIN, {"email": user.email, "password": "Brand-New-Secret-77"}
        ).status_code == 200
        # The refresh token issued before the change was revoked.
        assert api_client.post(REFRESH, {"refresh": tokens["refresh"]}).status_code == 401


# ---------------------------------------------------------------- logout
class TestLogout:
    def test_logout_blacklists_refresh_token(self, api_client, user, tokens_for):
        tokens = tokens_for(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = api_client.post(LOGOUT, {"refresh": tokens["refresh"]})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        api_client.credentials()
        assert api_client.post(REFRESH, {"refresh": tokens["refresh"]}).status_code == 401

    def test_logout_requires_authentication(self, api_client, user, tokens_for):
        refresh = tokens_for(user)["refresh"]

        response = api_client.post(LOGOUT, {"refresh": refresh})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_revoke_another_users_token(self, auth_client, other_user, tokens_for):
        bobs_refresh = tokens_for(other_user)["refresh"]

        response = auth_client.post(LOGOUT, {"refresh": bobs_refresh})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_twice_fails(self, api_client, user, tokens_for):
        tokens = tokens_for(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        api_client.post(LOGOUT, {"refresh": tokens["refresh"]})
        second = api_client.post(LOGOUT, {"refresh": tokens["refresh"]})

        assert second.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_token_rejected(self, auth_client):
        response = auth_client.post(LOGOUT, {"refresh": "garbage"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
