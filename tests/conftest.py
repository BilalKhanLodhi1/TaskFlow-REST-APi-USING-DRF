import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """An unauthenticated DRF test client. Later phases add an authenticated one."""
    return APIClient()
