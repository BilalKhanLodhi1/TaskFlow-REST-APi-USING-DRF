"""
Business logic for accounts that spans more than one model.

Keeping it here (instead of inside a view or serializer) makes it easy to
reuse and easy to test on its own.
"""

from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_all_refresh_tokens(user) -> int:
    """
    Blacklist every refresh token ever issued to `user`.

    Simple JWT records each refresh token it issues in OutstandingToken.
    Blacklisting them all means no existing session can obtain new access
    tokens. Returns the number of tokens newly revoked.
    """
    revoked = 0
    for outstanding in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        revoked += int(created)
    return revoked


@transaction.atomic
def change_password(user, new_password: str) -> None:
    """
    Set a new password and end every existing session.

    Wrapped in a transaction: if revoking tokens fails, the password change
    is rolled back too, so we never end up half-done.
    """
    user.set_password(new_password)
    user.save(update_fields=["password"])
    revoke_all_refresh_tokens(user)
