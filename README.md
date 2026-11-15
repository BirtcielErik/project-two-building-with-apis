# One More Chapter

A Django web app and REST API for keeping a personal bookshelf of
[Open Library](https://openlibrary.org) books, with ratings, private notes, and
read-only share links.

## Setup

Requires [uv](https://docs.astral.sh/uv/). Node.js is **not** needed.

```sh
uv sync                                   # install Python dependencies
cp .env.example .env                      # then fill in DJANGO_SECRET_KEY (see the file)
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py tailwind build   # compile the CSS (first run downloads the Tailwind CLI)
```

## Run

```sh
uv run --env-file .env python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

While editing templates, use `tailwind runserver` instead. It runs the dev server
and rebuilds the CSS whenever a template changes:

```sh
uv run --env-file .env python manage.py tailwind runserver
```

## API

Your API token is on the Profile page (**API access**). Send it in a header:

```sh
curl -H "Authorization: Token <your token>" "http://127.0.0.1:8000/api/entries/?status=finished&ordering=-rating"
```

| Endpoint | What it does |
| --- | --- |
| `GET /api/entries/` | Your shelf, 12 per page. Takes the same `q`, `status`, `min_rating`, `rated`, `ordering`, and `page` parameters as My Shelf. |
| `POST /api/entries/` | Add a book: send `work_key` (e.g. `OL27482W`) plus optional `status`, `rating`, `finished_on`. The server looks up the book itself. |
| `GET /api/entries/<id>/` | One entry, with its book nested (including `cover_url`). |
| `PUT` / `PATCH /api/entries/<id>/` | Change `status`, `rating`, and `finished_on`. Sending `work_key` is a 400. |
| `DELETE /api/entries/<id>/` | Remove the entry and its notes. |
| `GET` / `POST /api/entries/<id>/notes/` | List the entry's notes (newest first), or add one: `{"text": "..."}`. |
| `GET` / `DELETE /api/entries/<id>/notes/<note id>/` | One note, or delete it. Notes can't be edited (PUT/PATCH is a 405). |
| `GET /api/shared/<share token>/` | Public, read-only shared shelf (no token needed): book, status, rating, and finished date only. Never notes. |

While logged in, you can also open these URLs in the browser. Another user's
entry or note returns 404, and a missing or wrong token returns 401.

Errors: a bad, unknown, or duplicate work key is a 400; Open Library being down
is a 503, and an unreadable answer from it is a 502.

Rate limits: 60 requests a minute per user, and 10 a minute for adding entries
and for the shared endpoint. Going over returns 429 with a `Retry-After` header
(seconds to wait).

## Test and lint

Tests need no `.env` file and no internet connection. Any real network call
fails the test.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Configuration

All settings come from environment variables, documented in `.env.example`:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Signing secret. Required unless debug is on. |
| `DJANGO_DEBUG` | `true` turns debug on. Anything else (or unset) keeps it off. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names. |
| `OPENLIBRARY_CONTACT_EMAIL` | Contact email sent to Open Library in the User-Agent. |

## Project docs

- PRD: `prd/one-more-chapter.md`
- Implementation plan: `plans/one-more-chapter.md`
