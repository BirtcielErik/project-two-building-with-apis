# One More Chapter

A Django web app and REST API for keeping a personal bookshelf of Open Library books, with ratings, private notes, and read-only share links.

## Stack

- Python, Django, Django REST Framework, django-filter, SQLite
- Package manager: **uv**
- Lint/format: Ruff · Tests: Pytest (pytest-django, `responses`)
- UI: Tailwind CSS + DaisyUI (Forest theme) via `django-tailwind-cli` (no Node.js), HTMX vendored at a pinned version (no CDN)

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

## References

- PRD: `prd/one-more-chapter.md`
- Implementation plan: `plans/one-more-chapter.md`
- UI prototypes: `prototypes/my-shelf-layout.html`, `prototypes/book-detail-layout.html`
- Open Library research: `docs/research/book-and-music-apis.md`
