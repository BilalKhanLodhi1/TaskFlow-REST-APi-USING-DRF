"""
Phase 1 tests: prove the project boots, the health endpoint works,
the secure-by-default permission is active, and the docs are reachable.
None of these tests touch the database.
"""

from django.conf import settings
from django.urls import reverse
from rest_framework import status


def test_health_check_returns_ok(api_client):
    response = api_client.get(reverse("common:health-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "service": "taskflow-api"}


def test_health_check_rejects_post(api_client):
    response = api_client.post(reverse("common:health-check"))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_api_requires_authentication_by_default():
    permissions = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]

    assert "rest_framework.permissions.IsAuthenticated" in permissions


def test_openapi_schema_is_generated(api_client):
    response = api_client.get(reverse("schema"))

    assert response.status_code == status.HTTP_200_OK
    assert b"TaskFlow API" in response.content
    assert b"/api/v1/health/" in response.content


def test_all_local_apps_are_installed():
    expected = {
        "apps.common", "apps.accounts", "apps.projects", "apps.tasks",
        "apps.comments", "apps.attachments", "apps.notifications", "apps.activity",
    }

    assert expected.issubset(set(settings.INSTALLED_APPS))
