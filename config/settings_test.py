"""Settings used by the test suite.

Tests must run without a ``.env`` file, so this module supplies a throwaway
secret key before loading the normal settings.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-insecure-key")

from config.settings import *  # noqa: E402, F403

# Fast (insecure) password hashing keeps user-related tests quick.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
