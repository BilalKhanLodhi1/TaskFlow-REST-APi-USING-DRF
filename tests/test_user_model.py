import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_create_user_normalises_email_and_hashes_password():
    user = User.objects.create_user(email="  Ali@Example.COM ", password="pass-12345-xyz")

    assert user.email == "ali@example.com"
    assert user.password != "pass-12345-xyz"          # stored as a hash
    assert user.check_password("pass-12345-xyz")
    assert not user.is_staff and not user.is_superuser


def test_user_has_no_username_field():
    field_names = {field.name for field in User._meta.get_fields()}

    assert User.USERNAME_FIELD == "email"
    assert "username" not in field_names


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="pass-12345-xyz")


def test_create_superuser_sets_flags():
    admin = User.objects.create_superuser(email="admin@example.com", password="pass-12345-xyz")

    assert admin.is_staff and admin.is_superuser


def test_create_superuser_rejects_is_staff_false():
    with pytest.raises(ValueError):
        User.objects.create_superuser(email="a@example.com", password="x", is_staff=False)


def test_database_rejects_case_only_duplicate_email():
    User.objects.create_user(email="sara@example.com", password="pass-12345-xyz")

    # Bypass the manager on purpose: the DB constraint must still protect us.
    with pytest.raises(IntegrityError):
        User.objects.create(email="SARA@example.com")
