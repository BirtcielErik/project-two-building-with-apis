"""Tests for the custom user model."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import User


def test_project_uses_the_custom_user_model():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is User


@pytest.mark.django_db
def test_new_user_has_no_share_token_and_blank_display_name():
    user = User.objects.create_user(username="reader", password="a-long-password-123")

    assert user.share_token is None
    assert user.display_name == ""


@pytest.mark.django_db
def test_many_users_can_have_no_share_token():
    # share_token is unique, but several users with sharing off (None) must be allowed.
    User.objects.create_user(username="one", password="a-long-password-123")
    User.objects.create_user(username="two", password="a-long-password-123")

    assert User.objects.filter(share_token__isnull=True).count() == 2
