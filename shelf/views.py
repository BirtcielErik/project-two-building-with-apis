"""Website views for the shelf app."""

import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from shelf import openlibrary
from shelf.htmx import render_page_or_partial
from shelf.pagination import page_links

logger = logging.getLogger(__name__)


def landing(request: HttpRequest) -> HttpResponse:
    """Show the public landing page that explains what One More Chapter does.

    Logged-in users don't need the sales pitch, so they go straight to My Shelf.
    """
    if request.user.is_authenticated:
        return redirect("shelf:my_shelf")
    return render(request, "shelf/landing.html")


@login_required
def my_shelf(request: HttpRequest) -> HttpResponse:
    """Show the user's bookshelf.

    Books can't be saved yet (that arrives with search), so for now the
    shelf always shows its empty state with a button to the Search page.
    """
    return render(request, "shelf/my_shelf.html")


@login_required
def search(request: HttpRequest) -> HttpResponse:
    """Search Open Library and show one page of results (``?q=…&page=…``).

    HTMX requests get only the results area; normal requests get the full page,
    so a search URL can be bookmarked or reloaded.

    The template shows one ``state``:

    - ``start``: nothing searched yet (no ``q`` in the URL).
    - ``empty_query``: a blank search was submitted. No request is sent.
    - ``past_cap``: the page is past ``MAX_PAGE``. No request is sent.
    - ``unavailable`` / ``bad_response``: Open Library failed.
    - ``no_matches``: the search found nothing.
    - ``past_end``: the page is beyond the last page of results.
    - ``results``: a page of books, with pagination.
    """
    query = openlibrary.normalize_query(request.GET.get("q", ""))
    page = _parse_page(request.GET.get("page"))
    context: dict[str, object] = {"query": query, "page": page, "max_page": openlibrary.MAX_PAGE}

    if "q" not in request.GET:
        context["state"] = "start"
    elif not query:
        context["state"] = "empty_query"
    elif page > openlibrary.MAX_PAGE:
        context["state"] = "past_cap"
    else:
        context.update(_search_open_library(query, page))

    return render_page_or_partial(
        request, "shelf/search.html", "shelf/partials/search_results.html", context
    )


def _parse_page(raw: str | None) -> int:
    """Turn the ``page`` URL parameter into a page number, using 1 if it's missing or invalid."""
    try:
        page = int(raw or 1)
    except ValueError:
        return 1
    return max(page, 1)


def _search_open_library(query: str, page: int) -> dict[str, object]:
    """Run the search and return the template context for its outcome."""
    try:
        results_page = openlibrary.search(query, page)
    except openlibrary.OpenLibraryUnavailable:
        logger.warning("Open Library unavailable while searching for %r", query, exc_info=True)
        return {"state": "unavailable"}
    except openlibrary.OpenLibraryBadResponse:
        logger.warning("Bad response from Open Library for %r", query, exc_info=True)
        return {"state": "bad_response"}

    if results_page.total == 0:
        return {"state": "no_matches"}

    # Only the first MAX_PAGE pages can be browsed, so paginate at most that many results.
    browsable = min(results_page.total, openlibrary.MAX_PAGE * openlibrary.RESULTS_PER_PAGE)
    paginator = Paginator(range(browsable), openlibrary.RESULTS_PER_PAGE)
    if not results_page.results or page > paginator.num_pages:
        return {"state": "past_end", "total": results_page.total, "last_page": paginator.num_pages}

    return {
        "state": "results",
        "results": results_page.results,
        "total": results_page.total,
        "is_capped": results_page.total > browsable,
        "num_pages": paginator.num_pages,
        "page_links": page_links(paginator, page),
        "previous_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < paginator.num_pages else None,
    }
