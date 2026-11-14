"""The one place where One More Chapter talks to Open Library.

Every outbound request goes through this module. Views call its functions
through the module (``openlibrary.search(...)``), never via
``from shelf.openlibrary import search``, so tests can swap the functions out
with ``monkeypatch``.

Failures are reported with the exceptions defined below, so callers never have
to know about ``requests`` or HTTP status codes:

- ``OpenLibraryUnavailable``: Open Library is slow, down, or rate limiting us.
- ``OpenLibraryBadResponse``: Open Library answered with something we can't read.
"""

import hashlib
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.core.cache import cache

SEARCH_URL = "https://openlibrary.org/search.json"
# `default=false` makes a missing cover return 404 (so our placeholder shows)
# instead of Open Library's blank 1x1 image.
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg?default=false"
OPEN_LIBRARY_HOME = "https://openlibrary.org"

# Ask only for the fields we display, which keeps responses small and fast.
SEARCH_FIELDS = "key,title,author_name,first_publish_year,cover_i"
RESULTS_PER_PAGE = 20
# Browsing stops at page 50 (1,000 results); past that, refine the search.
MAX_PAGE = 50
TIMEOUT_SECONDS = 5
# Successful searches are kept in Django's in-memory cache for 10 minutes.
SEARCH_CACHE_SECONDS = 10 * 60

APP_NAME = "OneMoreChapter"
APP_VERSION = "0.1.0"

WORKS_PREFIX = "/works/"


# --- Exceptions --------------------------------------------------------------


class OpenLibraryError(Exception):
    """Base class for every Open Library failure. Catch this to catch them all."""


class OpenLibraryUnavailable(OpenLibraryError):
    """Open Library timed out, refused the connection, had a server error, or rate limited us."""


class OpenLibraryBadResponse(OpenLibraryError):
    """Open Library answered, but with invalid JSON or an unexpected structure."""


# --- Result types ------------------------------------------------------------


@dataclass(frozen=True)
class SearchResult:
    """One book (an Open Library *work*) from a search.

    ``work_key`` is stored without the ``/works/`` prefix, e.g. ``"OL27482W"``.
    """

    work_key: str
    title: str
    authors: list[str] = field(default_factory=list)
    first_publish_year: int | None = None
    cover_id: int | None = None


@dataclass(frozen=True)
class SearchPage:
    """One page of search results.

    ``total`` is how many books matched in all, across every page.
    """

    query: str
    page: int
    total: int
    results: list[SearchResult]


# --- Helpers -----------------------------------------------------------------


def cover_url(cover_id: int | None, size: str = "M") -> str | None:
    """Return the Open Library cover image URL for a cover ID, or ``None`` if there is none.

    ``size`` is ``"S"``, ``"M"``, or ``"L"`` (small, medium, large).
    """
    if not cover_id:
        return None
    return COVER_URL.format(cover_id=cover_id, size=size)


def work_url(work_key: str) -> str:
    """Return the public Open Library page for a work key like ``"OL27482W"``."""
    return f"{OPEN_LIBRARY_HOME}{WORKS_PREFIX}{work_key}"


def user_agent() -> str:
    """Identify this app to Open Library, including the contact email when one is configured.

    Open Library gives identified clients a higher rate limit (3 requests/second
    instead of 1) and asks every client to say who they are.
    """
    contact = settings.OPENLIBRARY_CONTACT_EMAIL
    if contact:
        return f"{APP_NAME}/{APP_VERSION} ({contact})"
    return f"{APP_NAME}/{APP_VERSION}"


def normalize_query(query: str) -> str:
    """Trim the query and collapse runs of whitespace into single spaces."""
    return " ".join(query.split())


# --- Public functions --------------------------------------------------------


def search(query: str, page: int = 1) -> SearchPage:
    """Search Open Library by title, author, or keyword and return one page of results.

    Raises ``ValueError`` for a blank query or a page outside 1..``MAX_PAGE``
    (callers should check these first so no request is wasted), and raises
    ``OpenLibraryUnavailable`` or ``OpenLibraryBadResponse`` when the request fails.
    """
    query = normalize_query(query)
    if not query:
        raise ValueError("The search query is blank.")
    if not 1 <= page <= MAX_PAGE:
        raise ValueError(f"The page must be between 1 and {MAX_PAGE}.")

    # Repeats of the same search (back button, paging back and forth) come from
    # the cache. Only successes get here, because failures raise before `set`.
    key = _search_cache_key(query, page)
    cached = cache.get(key)
    if cached is not None:
        return cached

    data = _get_json(
        SEARCH_URL,
        {"q": query, "fields": SEARCH_FIELDS, "limit": RESULTS_PER_PAGE, "page": page},
    )
    total, results = _parse_search(data)
    result_page = SearchPage(query=query, page=page, total=total, results=results)
    cache.set(key, result_page, SEARCH_CACHE_SECONDS)
    return result_page


def _search_cache_key(query: str, page: int) -> str:
    """Build the cache key for one page of a (normalized) search.

    Searches differing only in capitalization share a key. The query is hashed
    because cache keys must be short and free of spaces.
    """
    digest = hashlib.sha256(query.lower().encode()).hexdigest()
    return f"openlibrary:search:{digest}:{page}"


def _get_json(url: str, params: dict[str, str | int]) -> object:
    """Send a GET request to Open Library and return the decoded JSON body.

    Raises ``OpenLibraryUnavailable`` for timeouts, connection problems, server
    errors (5xx), and rate limiting (429). Raises ``OpenLibraryBadResponse`` for
    any other error status or a body that isn't valid JSON.
    """
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": user_agent()},
            timeout=TIMEOUT_SECONDS,
        )
    except (requests.Timeout, requests.ConnectionError) as error:
        raise OpenLibraryUnavailable("Open Library did not respond.") from error
    except requests.RequestException as error:
        raise OpenLibraryBadResponse(f"The request to Open Library failed: {error}") from error

    status = response.status_code
    if status == 429 or status >= 500:
        raise OpenLibraryUnavailable(f"Open Library returned HTTP {status}.")
    if status >= 400:
        raise OpenLibraryBadResponse(f"Open Library rejected the request (HTTP {status}).")

    try:
        return response.json()
    except ValueError as error:
        raise OpenLibraryBadResponse("Open Library returned invalid JSON.") from error


def _parse_search(data: object) -> tuple[int, list[SearchResult]]:
    """Turn a decoded ``search.json`` body into ``(total, results)``.

    Raises ``OpenLibraryBadResponse`` if the body doesn't have the expected shape:
    an object with an integer ``numFound`` and a list of ``docs`` objects.
    """
    if not isinstance(data, dict):
        raise OpenLibraryBadResponse("Open Library's search response was not a JSON object.")
    total = data.get("numFound")
    docs = data.get("docs")
    if not isinstance(total, int) or not isinstance(docs, list):
        raise OpenLibraryBadResponse("Open Library's search response is missing its results.")
    if not all(isinstance(doc, dict) for doc in docs):
        raise OpenLibraryBadResponse("Open Library's search results were not JSON objects.")

    results = [_parse_doc(doc) for doc in docs]
    return total, [result for result in results if result is not None]


def _parse_doc(doc: dict) -> SearchResult | None:
    """Turn one search document into a ``SearchResult``, or ``None`` if it isn't a work."""
    key = doc.get("key")
    if not isinstance(key, str) or not key.startswith(WORKS_PREFIX):
        return None
    return SearchResult(
        work_key=key.removeprefix(WORKS_PREFIX),
        title=doc.get("title") or "Untitled",
        authors=list(doc.get("author_name") or []),
        first_publish_year=doc.get("first_publish_year"),
        cover_id=doc.get("cover_i"),
    )
