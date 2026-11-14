"""Helpers that turn environment variables into Django settings values.

Environment variables are always strings (or missing), so these helpers do the
parsing in one place where tests can check it directly.
"""

from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured

# Only these values (ignoring case and surrounding spaces) switch a flag on.
TRUE_VALUES = {"1", "true", "yes", "on"}

# Used only when debug mode is on and no real key was provided. The prefix is
# Django's own convention for "never use this in production".
INSECURE_DEV_SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"


def read_debug(environ: Mapping[str, str]) -> bool:
    """Return whether debug mode is on, based on ``DJANGO_DEBUG``.

    Debug is off unless the variable is explicitly set to a yes-like value
    such as ``true`` or ``1``. Anything else, including ``"False"``, a typo,
    or a missing variable, keeps debug off.
    """
    value = environ.get("DJANGO_DEBUG", "")
    return value.strip().lower() in TRUE_VALUES


def read_list(environ: Mapping[str, str], name: str) -> list[str]:
    """Return a comma-separated environment variable as a list of strings.

    Blank items are dropped, so ``"a.com, ,b.com"`` becomes
    ``["a.com", "b.com"]`` and a missing variable becomes ``[]``.
    """
    raw = environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def read_secret_key(environ: Mapping[str, str], debug: bool) -> str:
    """Return the secret key from ``DJANGO_SECRET_KEY``.

    If no key is set, debug mode falls back to a clearly labeled insecure
    development key. Outside debug mode a missing key is a configuration
    error, so the app refuses to start rather than run insecurely.
    """
    key = environ.get("DJANGO_SECRET_KEY", "").strip()
    if key:
        return key
    if debug:
        return INSECURE_DEV_SECRET_KEY
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. Set it in your environment or .env file "
        "(see .env.example), or set DJANGO_DEBUG=true for local development."
    )
