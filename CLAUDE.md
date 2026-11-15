# One More Chapter

A Django web app and REST API for keeping a personal bookshelf of Open Library books, with ratings, private notes, and read-only share links.

## Stack

- Python, Django, Django REST Framework, django-filter, SQLite
- Package manager: **uv**
- Lint/format: Ruff · Tests: Pytest (pytest-django, `responses`)
- UI: Tailwind CSS + DaisyUI (Forest theme) via `django-tailwind-cli` (no Node.js), HTMX vendored at a pinned version (no CDN)

## Commands

- Dev server + CSS rebuild: `uv run --env-file .env python manage.py tailwind runserver`
- Build CSS: `uv run --env-file .env python manage.py tailwind build` (`assets/css/tailwind.css` is generated and git-ignored)
- Test: `uv run pytest` (no `.env` needed) · Lint: `uv run ruff check .` · Format: `uv run ruff format --check .`
- Migrate: `uv run --env-file .env python manage.py migrate`
- Demo data: `uv run --env-file .env python manage.py seed` (offline, re-runnable): `demo_maya` (sharing on) and `demo_theo`, password `one-more-chapter`

## Code style

- Write docstrings and type hints on every public function. The developer is a beginner, so this helps them understand the code.

## Architecture decisions (from the PRD)

- Django project package is `config`, with two apps: `accounts` (custom user, auth, profile) and `shelf` (books, entries, notes, Open Library, website views, API).
- Custom user model extends `AbstractUser` and must exist before the first migration; there is no separate Profile model.
- Book data is snapshotted into the local database so the shelf works when Open Library is down.
- All Open Library calls go through one service module, called via the module (not imported functions) so tests can replace them.
- Website and API share one FilterSet for shelf search, filters, ordering, and pagination.
- Owner data is always scoped to the requesting user; other users' objects return 404, never 403.
- Notes are always private: never shown on shared shelves or in the shared API.
- Views return a partial for HTMX requests and a full page otherwise.
- Configuration comes from environment variables; secrets stay out of the repo, and tests must run without a `.env` or network access.

## Shared building blocks (reuse, don't rebuild)

- `shelf/openlibrary.py`: Open Library service and its exceptions
- `shelf/saving.py`: `save_to_shelf()`, the one save flow for website and API (`SaveError`, `AlreadyOnShelf`)
- `shelf/filters.py`: `ShelfEntryFilter`, `TIEBREAK_ORDERING`, `status_counts()`
- `shelf/forms.py`: `ShelfEntryForm`, `NoteForm`; validation rules live on the models so serializers reuse them
- `shelf/views.py`: `_get_own_entry()` for owner-scoped 404s
- `accounts/models.py`: `new_share_token()`
- `shelf/htmx.py`: `is_htmx()`, `render_page_or_partial()`
- `shelf/pagination.py` + `templates/partials/pagination.html`: shortened page links
- `shelf/templates/shelf/partials/`: `book_row.html` (needs a `notes_count` annotation), `cover.html`, `stars.html`, `status_badge.html`
- `templates/partials/`: `field_errors.html`, `toasts.html` (`oob=True` in HTMX responses)
- `shelf/templatetags/shelf_extras.py`: `cover_url` filter
- `shelf/api.py` (`ShelfEntryViewSet`, scoped in `get_queryset()`; `NoteViewSet`, which 404s non-owned entries in `initial()`; public `SharedShelfView`; `OpenLibraryUnavailableError` 503 / `OpenLibraryBadResponseError` 502), `shelf/serializers.py` (`work_key` is create-only; `SharedShelfEntrySerializer` is the explicit public field list), `shelf/api_urls.py` (DRF router under `/api/` plus hand-written nested note routes)
- `assets/js/app.js`: `data-copy-target` (copies `data-secret` if present), `data-reveal-target` (masked secrets)

## Conventions

- Tests: `conftest.py` blocks the network, clears the cache, and provides `reader` and `logged_in_client` (logged in as `reader`); `shelf/tests/helpers.py` has `add_to_shelf()`. Test `openlibrary` with `responses`; test views by monkeypatching `openlibrary.<function>`.
- HTMX error states return 200 (HTMX doesn't swap 4xx/5xx). Loading: `hx-indicator` on a `.htmx-indicator` spinner plus `hx-disabled-elt`.
- HTMX success: a `*_response.html` wrapper = partial + `toasts.html` with `oob=True`. No-JS fallback: redirect with `messages.success`, or re-render the full page with errors.
- Confirmations (`assets/js/app.js`): plain forms use `data-confirm-dialog="<dialog id>"`; HTMX forms use `data-htmx-confirm="<dialog id>"`.
- Forms validated on the server get `novalidate`, so styled errors show instead of browser popups.
- API auth: `TokenAuthentication` is listed before `SessionAuthentication` so unauthenticated requests get 401 (not 403). API tests use the `token_client` fixture (`conftest.py`) or `rest_framework.test.APIClient` with `credentials(HTTP_AUTHORIZATION="Token …")`.
- API throttling: rates in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` (`user`, `entry_create`, `shared`). DRF reads them at import time, so tests use the real limits rather than overriding settings.
- `annotate(Count(...))` drops `Meta.ordering`: add `.order_by(*TIEBREAK_ORDERING)`, and keep such annotations off querysets used for other aggregates.

## References

- PRD: `prd/one-more-chapter.md`
- Implementation plan: `plans/one-more-chapter.md`
- UI prototypes: `prototypes/my-shelf-layout.html`, `prototypes/book-detail-layout.html`
- Open Library research: `docs/research/book-and-music-apis.md`
