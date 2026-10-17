import pytest

pytestmark = pytest.mark.django_db


def test_admin_user_pages_render(client, django_user_model):
    admin = django_user_model.objects.create_superuser(email="admin@example.com", password="x-Pass-123")
    client.force_login(admin)

    assert client.get("/admin/accounts/user/").status_code == 200
    assert client.get("/admin/accounts/user/add/").status_code == 200
    assert client.get(f"/admin/accounts/user/{admin.pk}/change/").status_code == 200
