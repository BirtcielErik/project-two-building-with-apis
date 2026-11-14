"""Database models for user accounts."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A One More Chapter user.

    Extends Django's built-in user (username, password, etc.) with the extra
    fields this app needs. There is no separate Profile model.
    """

    share_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        default=None,
        help_text="Secret token for the public shared-shelf link. Empty means sharing is off.",
    )
    display_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Optional name shown on the shared shelf instead of the username.",
    )

    def __str__(self) -> str:
        """Return the username, which is how users are shown in the admin."""
        return self.username
