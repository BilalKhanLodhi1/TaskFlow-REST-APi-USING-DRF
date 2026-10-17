from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import User


class UserCreationForm(DjangoUserCreationForm):
    """Admin "Add user" form, based on email instead of username."""

    class Meta:
        model = User
        fields = ("email",)


class UserChangeForm(DjangoUserChangeForm):
    """Admin "Change user" form for our User model."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
