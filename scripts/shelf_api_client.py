"""Talk to the One More Chapter REST API from the command line.

Two commands:

    list    GET  /api/entries/       Search and filter your shelf with query parameters.
    update  PATCH /api/entries/<id>/ Change ONE field of one entry and show before/after.

Setup (once):
    1. Start the site:  uv run --env-file .env python manage.py tailwind runserver
    2. Log in, open Profile -> API access, and copy your token.
    3. Add it to your .env file (git ignores .env, so the token stays private):
           SHELF_API_TOKEN=<your token>
       Optional: SHELF_API_URL (defaults to http://127.0.0.1:8000/api).

Examples:
    uv run --env-file .env python scripts/shelf_api_client.py list --status finished --ordering=-rating
    uv run --env-file .env python scripts/shelf_api_client.py list --q weir --page 1
    uv run --env-file .env python scripts/shelf_api_client.py update 149 rating 5
    uv run --env-file .env python scripts/shelf_api_client.py update 149 status finished
    uv run --env-file .env python scripts/shelf_api_client.py update 149 rating none

(Use --ordering=-rating with an "=", otherwise the leading "-" looks like an option.)
"""

import argparse
import os
import sys
from typing import Any

import requests

DEFAULT_API_URL = "http://127.0.0.1:8000/api"
TIMEOUT_SECONDS = 10

# The values the API accepts, copied from shelf/models.py and shelf/filters.py
# so argparse can reject typos before any request is sent.
STATUS_CHOICES = ["tbr", "reading", "finished", "dnf"]
RATED_CHOICES = ["yes", "no"]
ORDERING_CHOICES = [
    "added", "-added", "title", "-title", "author", "-author", "rating", "-rating",
    "finished", "-finished", "updated", "-updated",
]
# Fields an API client may change with PATCH (the book itself can't change).
UPDATABLE_FIELDS = ["status", "rating", "finished_on"]


class ApiError(Exception):
    """Raised when an API call fails. The message is meant to be shown to the user."""


# --- Talking to the API ------------------------------------------------------


def make_session() -> tuple[requests.Session, str]:
    """Build a ``requests`` session that sends the API token on every request.

    Returns the session and the API's base URL (without a trailing slash).
    Raises ``ApiError`` if ``SHELF_API_TOKEN`` isn't set.
    """
    token = os.environ.get("SHELF_API_TOKEN", "").strip()
    if not token:
        raise ApiError(
            "SHELF_API_TOKEN is not set. Copy your token from Profile -> API access, "
            "add SHELF_API_TOKEN=<token> to .env, and run with --env-file .env."
        )
    # "or" also covers a blank "SHELF_API_URL=" line copied from .env.example.
    base_url = (os.environ.get("SHELF_API_URL", "").strip() or DEFAULT_API_URL).rstrip("/")

    session = requests.Session()
    # DRF's TokenAuthentication expects exactly this header format.
    session.headers.update({"Authorization": f"Token {token}", "Accept": "application/json"})
    return session, base_url


def call_api(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one request and return the decoded JSON body.

    Network problems and error status codes are turned into an ``ApiError``
    with a readable message (including DRF's own error details for a 400).
    """
    try:
        response = session.request(method, url, params=params, json=json, timeout=TIMEOUT_SECONDS)
    except requests.ConnectionError:
        raise ApiError(f"Could not connect to {url}. Is the dev server running?") from None
    except requests.Timeout:
        raise ApiError(f"No answer from the API within {TIMEOUT_SECONDS} seconds.") from None

    if response.ok:
        return response.json()

    # DRF error bodies are JSON, e.g. {"detail": "..."} or {"rating": ["..."]}.
    try:
        details = response.json()
    except ValueError:
        details = response.text[:200]

    messages = {
        400: f"The API rejected the request: {details}",
        401: "The token was missing or wrong (401). Check SHELF_API_TOKEN.",
        404: "Not found (404). That entry doesn't exist or isn't on your shelf.",
        429: f"Too many requests (429). Wait {response.headers.get('Retry-After', 'a few')} "
        "seconds and try again.",
    }
    raise ApiError(messages.get(response.status_code, f"HTTP {response.status_code}: {details}"))


# --- Behavior 1: list with query parameters ------------------------------------


def list_entries(session: requests.Session, base_url: str, filters: dict[str, Any]) -> None:
    """GET ``/api/entries/`` with the given filters and print one page of results."""
    # Leave out options the user didn't give, so the URL only has real filters.
    params = {name: value for name, value in filters.items() if value is not None}
    data = call_api(session, "GET", f"{base_url}/entries/", params=params)

    print(f"GET {base_url}/entries/  params={params or '(none)'}")
    print(f"{data['count']} matching entr{'y' if data['count'] == 1 else 'ies'}; "
          f"showing {len(data['results'])} on this page.\n")

    for entry in data["results"]:
        print_entry(entry)

    if data["next"]:
        print(f"More results: next page is {data['next']}")


# --- Behavior 2: update one field ----------------------------------------------


def parse_field_value(field: str, raw: str) -> str | int | None:
    """Turn the command-line text into the JSON value the API expects for ``field``.

    ``none`` (any case) clears an optional field, which becomes JSON ``null``.
    Ratings are sent as numbers; dates and statuses stay strings.
    """
    if raw.lower() == "none":
        return None
    if field == "rating":
        try:
            return int(raw)
        except ValueError:
            raise ApiError(f"A rating must be a whole number from 1 to 5, not {raw!r}.") from None
    return raw


def update_entry(session: requests.Session, base_url: str, entry_id: int, field: str, raw: str) -> None:
    """PATCH one field of one entry, printing the entry before and after."""
    url = f"{base_url}/entries/{entry_id}/"
    value = parse_field_value(field, raw)

    before = call_api(session, "GET", url)
    print(f"BEFORE  (GET {url})")
    print_entry(before)

    # PATCH (not PUT) sends only the field being changed; the rest stay as they are.
    after = call_api(session, "PATCH", url, json={field: value})
    print(f"AFTER   (PATCH {url}  body={{{field!r}: {value!r}}})")
    print_entry(after)

    print(f"Changed {field}: {before[field]!r} -> {after[field]!r}")


# --- Output --------------------------------------------------------------------


def print_entry(entry: dict[str, Any]) -> None:
    """Print one shelf entry (as the API returns it) as a short block of text."""
    book = entry["book"]
    # Plain "4/5" rather than stars: the Windows console can't print "★".
    rating = f"{entry['rating']}/5" if entry["rating"] else "(not rated)"
    print(f"  #{entry['id']}  {book['title']} by {book['authors'] or '(unknown author)'}")
    print(f"        status: {entry['status']:<9} rating: {rating}  "
          f"finished: {entry['finished_on'] or '-'}")
    print(f"        updated: {entry['updated_at']}")
    print()


# --- Command line --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Describe the ``list`` and ``update`` commands and their options."""
    parser = argparse.ArgumentParser(description="Use the One More Chapter shelf API.")
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="list your shelf entries with filters")
    list_cmd.add_argument("--q", help="search title or author")
    list_cmd.add_argument("--status", choices=STATUS_CHOICES)
    list_cmd.add_argument("--min-rating", type=int, choices=range(1, 6), dest="min_rating")
    list_cmd.add_argument("--rated", choices=RATED_CHOICES)
    list_cmd.add_argument("--ordering", choices=ORDERING_CHOICES)
    list_cmd.add_argument("--page", type=int)

    update_cmd = commands.add_parser("update", help="change one field of one entry")
    update_cmd.add_argument("entry_id", type=int, help="the entry's id, e.g. 149")
    update_cmd.add_argument("field", choices=UPDATABLE_FIELDS)
    update_cmd.add_argument("value", help='new value, e.g. 5, finished, 2026-11-01, or "none"')
    return parser


def main() -> int:
    """Run the chosen command and return the process exit code (0 = success)."""
    args = build_parser().parse_args()
    try:
        session, base_url = make_session()
        if args.command == "list":
            filters = {
                "q": args.q,
                "status": args.status,
                "min_rating": args.min_rating,
                "rated": args.rated,
                "ordering": args.ordering,
                "page": args.page,
            }
            list_entries(session, base_url, filters)
        else:
            update_entry(session, base_url, args.entry_id, args.field, args.value)
    except ApiError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
