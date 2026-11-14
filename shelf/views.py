"""Website views for the shelf app."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from shelf import openlibrary, saving
from shelf.htmx import is_htmx, render_page_or_partial
from shelf.models import ShelfEntry
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
    """Show the user's bookshelf, newest additions first.

    Everything comes from our own database, so the shelf works even when
    Open Library is down. An empty shelf shows a button to the Search page.
    """
    entries = request.user.shelf_entries.select_related("book").order_by("-added_at")
    return render(request, "shelf/my_shelf.html", {"entries": entries})


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
        if context["state"] == "results":
            context["rows"] = _mark_saved(request, context["results"])

    return render_page_or_partial(
        request, "shelf/search.html", "shelf/partials/search_results.html", context
    )


@login_required
@require_POST
def save_book(request: HttpRequest) -> HttpResponse:
    """Save a search result to the user's shelf (POST ``work_key`` and optional ``status``).

    HTMX requests get the result row's save area back: "✓ On your shelf" plus
    a toast on success, or the Save button with an inline error on failure.
    Without JavaScript, the browser is sent back to the search page (``next``)
    with the outcome as a message.
    """
    work_key = request.POST.get("work_key", "").strip()
    status = request.POST.get("status") or ShelfEntry.Status.TO_BE_READ
    next_url = _safe_next_url(request)
    entry: ShelfEntry | None = None
    error = ""

    try:
        entry = saving.save_to_shelf(request.user, work_key, status)
    except saving.AlreadyOnShelf as already:
        entry = already.entry  # Nothing to fix: just show where it is.
    except saving.SaveError as save_error:
        error = str(save_error)
    except openlibrary.OpenLibraryUnavailable:
        logger.warning("Open Library unavailable while saving %r", work_key, exc_info=True)
        error = "Open Library isn't responding right now. Please try again in a moment."
    except openlibrary.OpenLibraryBadResponse:
        logger.warning("Bad response from Open Library while saving %r", work_key, exc_info=True)
        error = "Open Library sent back something we couldn't read. Please try again."
    else:
        messages.success(
            request, f"Saved “{entry.book.title}” to your shelf as {entry.get_status_display()}."
        )

    if not is_htmx(request):
        if error:
            messages.error(request, error)
        return redirect(next_url)

    context = {
        "work_key": work_key,
        "saved_entry_id": entry.pk if entry else None,
        "save_error": error,
        "next_url": next_url,
    }
    return render(request, "shelf/partials/save_response.html", context)


def _mark_saved(
    request: HttpRequest, results: list[openlibrary.SearchResult]
) -> list[tuple[openlibrary.SearchResult, int | None]]:
    """Pair each search result with the user's entry ID for it (``None`` if it isn't saved).

    One database query covers the whole page of results.
    """
    keys = [result.work_key for result in results]
    saved = dict(
        ShelfEntry.objects.filter(user=request.user, book__ol_work_key__in=keys).values_list(
            "book__ol_work_key", "pk"
        )
    )
    return [(result, saved.get(result.work_key)) for result in results]


def _safe_next_url(request: HttpRequest) -> str:
    """Return the posted ``next`` URL if it points to this site, else the Search page.

    Checking the host stops a crafted form from redirecting users to another site.
    """
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return reverse("shelf:search")


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
