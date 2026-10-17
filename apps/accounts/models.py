from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractUser):
    """
    TaskFlow's user model.

    We inherit from AbstractUser to keep everything Django already provides
    (password hashing, is_active, is_staff, permissions, groups, last_login,
    date_joined, first_name, last_name) and change only one thing: users log
    in with their email address instead of a username.
    """

    username = None  # remove the inherited username field entirely
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"   # the field used to log in
    REQUIRED_FIELDS = []       # extra prompts for `createsuperuser` (email + password are automatic)

    objects = UserManager()

    class Meta:
        ordering = ["email"]
        constraints = [
            # Defence in depth: even if some code path skips the manager's
            # lowercasing, the database itself rejects case-only duplicates.
            models.UniqueConstraint(Lower("email"), name="unique_user_email_case_insensitive"),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
