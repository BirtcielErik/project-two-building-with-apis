"""Django settings for the One More Chapter project.

Values that change between machines (secrets, debug, hosts, contact email)
come from environment variables. Locally they are loaded from a git-ignored
``.env`` file with ``uv run --env-file .env ...``; see ``.env.example``.
"""

import os
from pathlib import Path

from config import env

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Environment-based settings ---------------------------------------------

DEBUG = env.read_debug(os.environ)
SECRET_KEY = env.read_secret_key(os.environ, debug=DEBUG)
ALLOWED_HOSTS = env.read_list(os.environ, "DJANGO_ALLOWED_HOSTS")

# Sent to Open Library in the User-Agent so they can contact us (and so we get
# the higher rate limit for identified clients). Empty means "not provided".
OPENLIBRARY_CONTACT_EMAIL = os.environ.get("OPENLIBRARY_CONTACT_EMAIL", "").strip()


# --- Application definition --------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tailwind_cli",
    "accounts",
    "shelf",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database ----------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Our own user model (accounts.User). It must exist before the first migration.
AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Cache -------------------------------------------------------------------

# In-memory cache, used later for Open Library search results and API throttling.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "one-more-chapter",
    }
}


# --- Password validation -----------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internationalization ----------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files (CSS, JavaScript, images) ----------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "assets"]
STATIC_ROOT = BASE_DIR / "staticfiles"


# --- Tailwind CSS + DaisyUI (django-tailwind-cli) ------------------------------

# Download "tailwind-cli-extra", a Tailwind CLI build that includes DaisyUI.
TAILWIND_CLI_USE_DAISY_UI = True
# Pinned so every machine builds with the same Tailwind (4.3.4) + DaisyUI (5.7.50).
TAILWIND_CLI_VERSION = "2.10.35"
# Our own input CSS file, which turns on DaisyUI with Forest as the default theme.
# It sits outside STATICFILES_DIRS so the raw source is never served.
TAILWIND_CLI_SRC_CSS = "tailwind/source.css"
# Where the compiled CSS is written (inside STATICFILES_DIRS[0]).
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"


# --- Email -------------------------------------------------------------------

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
