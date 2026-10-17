from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Manager for our email-based User model.

    Django's default manager expects a `username`. Ours has no username, so
    we teach Django how to create normal users and superusers from an email.
    """

    use_in_migrations = True

    @staticmethod
    def normalize_email_address(email: str) -> str:
        # Store every email in lowercase so "Ali@Mail.com" and "ali@mail.com"
        # can never become two separate accounts.
        return email.strip().lower()

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email_address(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes the password; never store plain text
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Used by Django's authentication backend at login time.
        # A case-insensitive match lets users log in regardless of letter case.
        return self.get(email__iexact=email)
