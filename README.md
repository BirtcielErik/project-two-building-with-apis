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

## Demo data

The `seed` command creates two demo users with realistic shelves (books,
statuses, ratings, finished dates, and notes), so you can try the site and API
without adding books by hand:

```sh
uv run --env-file .env python manage.py seed
```

| Username | Password | Shelf |
| --- | --- | --- |
| `demo_maya` | `one-more-chapter` | 18 books, share link **on** |
| `demo_theo` | `one-more-chapter` | 16 books, sharing off |

- **Works offline.** The book data is stored in
  `shelf/management/commands/seed.py`, so seeding never calls Open Library.
- **Safe to run again.** Each run resets the two demo users' passwords and
  shelves to the original data. Other users are never touched, and
  `demo_maya`'s share link and both users' API tokens stay the same.
- **Entry IDs change on every run.** The shelves are deleted and re-created,
  so an ID like `/api/entries/149/` won't exist after reseeding. Look up the
  new IDs on My Shelf or with `GET /api/entries/`.
- These are for exploring a local copy only. Don't run `seed` on a public
  server, because everyone knows the password.

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

### API client script

`scripts/shelf_api_client.py` uses the API from the command line. It can list
your shelf with filters, or change one field of one entry and print the entry
before and after.

**Setup (once):** start the dev server, log in, and copy your token from
**Profile → API access**. Then add it to `.env` (git ignores this file, so the
token stays private):

```sh
SHELF_API_TOKEN=<your token>
# Optional; defaults to http://127.0.0.1:8000/api
SHELF_API_URL=
```

**Run** (with the dev server running in another terminal). Always include
`--env-file .env`, which is how the script gets your token:

```sh
# List: GET /api/entries/ with query parameters
uv run --env-file .env python scripts/shelf_api_client.py list --status finished --ordering=-rating
uv run --env-file .env python scripts/shelf_api_client.py list --q weir --min-rating 4 --page 1

# Update one field: GET (before), then PATCH /api/entries/<id>/ (after)
uv run --env-file .env python scripts/shelf_api_client.py update 149 rating 5
uv run --env-file .env python scripts/shelf_api_client.py update 149 status finished
uv run --env-file .env python scripts/shelf_api_client.py update 149 rating none   # "none" clears it

# All options
uv run python scripts/shelf_api_client.py --help
```

- `list` options: `--q`, `--status` (`tbr`, `reading`, `finished`, `dnf`),
  `--min-rating` (1–5), `--rated` (`yes`/`no`), `--ordering`, `--page`. Write
  `--ordering=-rating` with an `=`, or the leading `-` looks like another option.
- `update` fields: `status`, `rating`, or `finished_on` (`YYYY-MM-DD`).
- Entry IDs come from the `list` output (for example `#149`). The examples use
  an ID from `demo_maya`'s [seeded shelf](#demo-data). Your IDs will be
  different, and they change each time you run `seed`.

**Testing it by hand:** the script has no automated tests. These checks show
it is working:

| Try | Expected |
| --- | --- |
| `list`, then `list --status finished` | The second list only has finished books |
| `update 149 rating 5`, then open `/api/entries/149/` in the browser | Both show a rating of 5 |
| `update 149 rating 9` | `Error: … less than or equal to 5`; nothing changes |
| `update` on another user's entry | `Not found (404)` |
| Run without `--env-file .env` | `SHELF_API_TOKEN is not set` |
| Stop the dev server, then run `list` | `Could not connect… Is the dev server running?` |

The script exits with 0 on success and 1 on any error. To undo your test
changes, run `seed` again (see [Demo data](#demo-data)). Then run `list` to
find the new entry IDs.

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
| `SHELF_API_TOKEN` | Your API token, used only by `scripts/shelf_api_client.py`. |
| `SHELF_API_URL` | API base URL for the script. Defaults to `http://127.0.0.1:8000/api`. |

## Project docs

- PRD: `prd/one-more-chapter.md`
- Implementation plan: `plans/one-more-chapter.md`
