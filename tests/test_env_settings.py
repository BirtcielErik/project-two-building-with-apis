"""Tests for reading Django settings from environment variables."""

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config import env


@pytest.mark.parametrize(
    ("environ", "expected_debug"),
    [
        ({}, False),  # missing -> off
        ({"DJANGO_DEBUG": ""}, False),
        ({"DJANGO_DEBUG": "False"}, False),  # a non-empty string, but still off
        ({"DJANGO_DEBUG": "0"}, False),
        ({"DJANGO_DEBUG": "no"}, False),
        ({"DJANGO_DEBUG": "True"}, True),
        ({"DJANGO_DEBUG": "true"}, True),
        ({"DJANGO_DEBUG": "1"}, True),
        ({"DJANGO_DEBUG": " yes "}, True),
        ({"DJANGO_DEBUG": "on"}, True),
    ],
)
def test_debug_is_off_unless_explicitly_enabled(environ, expected_debug):
    assert env.read_debug(environ) is expected_debug


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ("", []),
        ("localhost", ["localhost"]),
        ("localhost, 127.0.0.1 ,,example.com", ["localhost", "127.0.0.1", "example.com"]),
    ],
)
def test_allowed_hosts_are_read_as_a_comma_separated_list(raw, expected):
    environ = {} if raw is None else {"DJANGO_ALLOWED_HOSTS": raw}
    assert env.read_list(environ, "DJANGO_ALLOWED_HOSTS") == expected


def test_env_example_documents_every_setting():
    text = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")
    for name in (
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "OPENLIBRARY_CONTACT_EMAIL",
    ):
        assert f"{name}=" in text


def test_secret_key_rules():
    # A real key from the environment is always used.
    real = {"DJANGO_SECRET_KEY": "a-real-secret"}
    assert env.read_secret_key(real, debug=False) == "a-real-secret"
    assert env.read_secret_key(real, debug=True) == "a-real-secret"

    # Without a key, debug mode falls back to a clearly labeled insecure key.
    dev_key = env.read_secret_key({}, debug=True)
    assert dev_key.startswith("django-insecure-")

    # Without a key and without debug, startup must fail loudly.
    with pytest.raises(ImproperlyConfigured):
        env.read_secret_key({}, debug=False)
    with pytest.raises(ImproperlyConfigured):
        env.read_secret_key({"DJANGO_SECRET_KEY": "   "}, debug=False)
