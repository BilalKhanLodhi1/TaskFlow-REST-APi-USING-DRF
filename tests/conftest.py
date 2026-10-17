import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

TEST_PASSWORD = "Str0ng-Test-Passw0rd!"


@pytest.fixture(autouse=True)
def fast_password_hashing(settings):
    """
    Real password hashing is deliberately slow (that's what makes it secure).
    Tests don't need that protection, so use a fast hasher to keep them quick.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def reset_throttle_cache():
    """Throttle counters live in the cache; clear them so tests don't affect each other."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    """An unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def password() -> str:
    return TEST_PASSWORD


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="alice@example.com", password=TEST_PASSWORD, first_name="Alice", last_name="Khan"
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        email="bob@example.com", password=TEST_PASSWORD, first_name="Bob", last_name="Ali"
    )


@pytest.fixture
def tokens_for(api_client):
    """Log a user in through the real endpoint and return {"access", "refresh"}."""

    def _login(user, password=TEST_PASSWORD) -> dict:
        response = api_client.post(
            "/api/v1/auth/token/", {"email": user.email, "password": password}
        )
        assert response.status_code == 200, response.content
        return response.json()

    return _login


@pytest.fixture
def auth_client(user, tokens_for) -> APIClient:
    """A client authenticated as `user` with a real JWT access token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for(user)['access']}")
    return client
