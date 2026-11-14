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
- `shelf/htmx.py`: `render_page_or_partial()`
- `shelf/pagination.py` + `templates/partials/pagination.html`: shortened page links
- `shelf/templates/shelf/partials/book_row.html`, `cover.html`: list row and cover with placeholder
- `shelf/templatetags/shelf_extras.py`: `cover_url` filter

## Conventions

- Tests: `conftest.py` blocks the network, clears the cache, and provides `logged_in_client`. Test `openlibrary` with `responses`; test views by monkeypatching `openlibrary.<function>`.
- HTMX error states return 200 (HTMX doesn't swap 4xx/5xx). Loading: `hx-indicator` on a `.htmx-indicator` spinner plus `hx-disabled-elt`.

## References

- PRD: `prd/one-more-chapter.md`
- Implementation plan: `plans/one-more-chapter.md`
- UI prototypes: `prototypes/my-shelf-layout.html`, `prototypes/book-detail-layout.html`
- Open Library research: `docs/research/book-and-music-apis.md`
