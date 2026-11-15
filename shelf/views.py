"""Website views for the shelf app."""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from shelf import openlibrary, saving
from shelf.filters import (
    MIN_RATING_CHOICES,
    ORDERING_CHOICES,
    PAGE_SIZE,
    RATED_CHOICES,
    TIEBREAK_ORDERING,
    ShelfEntryFilter,
    status_counts,
)
from shelf.forms import NoteForm, ShelfEntryForm
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
    """Show the user's bookshelf with search, filters, sorting, and pagination.

    The URL parameters (``q``, ``status``, ``min_rating``, ``rated``,
    ``ordering``, ``page``) go through the shared ``ShelfEntryFilter``, so a
    bookmarked URL shows the same view. HTMX requests get only the results
    area; the sidebar, search box, and Currently Reading strip stay in place.

    Everything comes from our own database, so the shelf works even when
    Open Library is down. An empty shelf shows a button to the Search page.
    """
    shelf = request.user.shelf_entries.select_related("book")
    # Each row shows its notes count. Only the list gets this count: joining
    # notes into the status counts below would count each book once per note.
    # Counting groups the query, and Django then ignores the model's default
    # ordering, so the default sort is set here. A chosen sort replaces it.
    listed = shelf.annotate(notes_count=Count("notes")).order_by(*TIEBREAK_ORDERING)
    filterset = ShelfEntryFilter(request.GET, queryset=listed)
    # Invalid values (like min_rating=9) are dropped from cleaned_data, so they're ignored.
    filterset.is_valid()
    chosen = filterset.form.cleaned_data

    paginator = Paginator(filterset.qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    # Counted over the whole shelf (not filterset.qs), so the sidebar always shows every status.
    counts = status_counts(shelf)
    shelf_total = sum(counts.values())

    context = {
        "page_obj": page_obj,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "page_links": page_links(paginator, page_obj.number),
        "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        "shelf_total": shelf_total,
        "query": chosen.get("q") or "",
        "status_options": _status_options(chosen.get("status") or "", counts, shelf_total),
        "rating_options": _options(MIN_RATING_CHOICES, chosen.get("min_rating")),
        "rated_options": _options(RATED_CHOICES, chosen.get("rated")),
        "ordering_options": _options(ORDERING_CHOICES, (chosen.get("ordering") or [""])[0]),
        # The strip always shows every Currently Reading book, whatever the filters.
        "reading_now": shelf.filter(status=ShelfEntry.Status.READING),
    }
    return render_page_or_partial(
        request, "shelf/my_shelf.html", "shelf/partials/shelf_results.html", context
    )


def _options(choices: list[tuple[str, str]], current: object) -> list[dict[str, object]]:
    """Turn ``(value, label)`` choices into dicts that also say which one is selected.

    ``current`` may be a number or ``None`` (from the form), so it's compared as text.
    """
    current_text = "" if current is None else str(current)
    return [
        {"value": value, "label": label, "checked": value == current_text}
        for value, label in choices
    ]


def _status_options(current: str, counts: dict[str, int], total: int) -> list[dict[str, object]]:
    """Return the sidebar's status choices ("All books" first), each with its book count."""
    options = _options([("", "All books"), *ShelfEntry.Status.choices], current)
    for option in options:
        option["count"] = counts.get(option["value"], 0) if option["value"] else total
    return options


@login_required
def entry_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Show one book on the user's shelf, with the form for its reading details.

    Like My Shelf, this page only reads our own database, so it works even
    when Open Library is down.
    """
    entry = _get_own_entry(request, pk)
    return _render_detail(request, entry, ShelfEntryForm(instance=entry))


def _get_own_entry(request: HttpRequest, pk: int) -> ShelfEntry:
    """Return the logged-in user's shelf entry ``pk``, or raise a 404.

    Another user's entry is "not found" too (never "forbidden"), so nobody can
    discover which entry IDs exist on other people's shelves.
    """
    return get_object_or_404(ShelfEntry.objects.select_related("book"), pk=pk, user=request.user)


def _render_detail(
    request: HttpRequest,
    entry: ShelfEntry,
    form: ShelfEntryForm,
    note_form: NoteForm | None = None,
) -> HttpResponse:
    """Render the full book detail page for ``entry``.

    ``form`` is the reading form, and ``note_form`` the add-note form (a blank
    one if not given), so either can be shown with its errors.
    """
    context = {
        **_notes_context(entry, note_form or NoteForm()),
        "form": form,
        "open_library_url": openlibrary.work_url(entry.book.ol_work_key),
    }
    return render(request, "shelf/entry_detail.html", context)


@login_required
@require_POST
def entry_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Save the status, rating, and finished date posted from the detail page's form.

    All three are saved together, or none are if any is invalid. HTMX requests
    get the form back, with "Saved ✓" or the errors next to their fields.
    Without JavaScript, a successful save goes back to the detail page with a
    toast, and a failed one shows the full page with the errors.
    """
    entry = _get_own_entry(request, pk)
    form = ShelfEntryForm(request.POST, instance=entry)
    saved = form.is_valid()
    if saved:
        form.save()

    if not is_htmx(request):
        if not saved:
            return _render_detail(request, entry, form)
        messages.success(request, "Saved your reading details.")
        return redirect("shelf:entry_detail", pk=entry.pk)

    return render(
        request,
        "shelf/partials/reading_form.html",
        {"entry": entry, "form": form, "saved": saved},
    )


@login_required
@require_POST
def entry_remove(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove a book from the user's shelf, then go back to My Shelf with a toast."""
    entry = _get_own_entry(request, pk)
    title = entry.book.title
    entry.delete()
    messages.success(request, f"Removed “{title}” from your shelf.")
    return redirect("shelf:my_shelf")


@login_required
@require_POST
def note_add(request: HttpRequest, pk: int) -> HttpResponse:
    """Add a note to one of the user's shelf entries.

    HTMX requests get the notes section back: the new note at the top and a
    toast, or the add box with an error under it (nothing is saved). Without
    JavaScript, a saved note goes back to the detail page, and an empty one
    shows the full page with the error.
    """
    entry = _get_own_entry(request, pk)
    form = NoteForm(request.POST)
    saved = form.is_valid()
    if saved:
        form.instance.entry = entry
        form.save()
        messages.success(request, "Note added.")

    if not is_htmx(request):
        if not saved:
            return _render_detail(request, entry, ShelfEntryForm(instance=entry), note_form=form)
        return redirect(f"{reverse('shelf:entry_detail', args=[entry.pk])}#notes")

    # After a save the add box starts empty again; after an error it keeps the text.
    note_form = NoteForm() if saved else form
    return render(request, "shelf/partials/notes_response.html", _notes_context(entry, note_form))


@login_required
@require_POST
def note_delete(request: HttpRequest, pk: int, note_pk: int) -> HttpResponse:
    """Delete one note from one of the user's shelf entries, then show a toast.

    The note must belong to that entry, and the entry to the user; otherwise
    it's a 404. HTMX requests get the updated notes section back; without
    JavaScript the browser goes back to the detail page.
    """
    entry = _get_own_entry(request, pk)
    get_object_or_404(entry.notes, pk=note_pk).delete()
    messages.success(request, "Note deleted.")

    if not is_htmx(request):
        return redirect(f"{reverse('shelf:entry_detail', args=[entry.pk])}#notes")
    return render(request, "shelf/partials/notes_response.html", _notes_context(entry, NoteForm()))


def _notes_context(entry: ShelfEntry, note_form: NoteForm) -> dict[str, object]:
    """Return what the notes section needs: the entry, its notes (newest first), the add form."""
    return {"entry": entry, "notes": list(entry.notes.all()), "note_form": note_form}


# The shared shelf's groups, in the order they're shown, each with its sort order.
# Finished books show the most recently finished first (books with no date last);
# the other groups show the most recently added first.
SHARED_GROUPS: list[tuple[str, tuple[object, ...]]] = [
    (ShelfEntry.Status.READING, TIEBREAK_ORDERING),
    (ShelfEntry.Status.FINISHED, (F("finished_on").desc(nulls_last=True), *TIEBREAK_ORDERING)),
    (ShelfEntry.Status.TO_BE_READ, TIEBREAK_ORDERING),
    (ShelfEntry.Status.DID_NOT_FINISH, TIEBREAK_ORDERING),
]
# How many books each group shows at first, and how many each "Show more" adds.
SHARED_GROUP_SIZE = 12


def shared_shelf(request: HttpRequest, share_token: str) -> HttpResponse:
    """Show a user's shelf, read-only, to anyone who has its share link.

    No login is needed. A token that doesn't match any user (wrong, regenerated,
    or disabled) is "not found". Books are grouped by status, empty groups are
    left out, and each group shows ``SHARED_GROUP_SIZE`` books at first.

    "Show more" asks for ``?group=<status>&page=<n>``:

    - HTMX requests get just that group's next books (and the next "Show more").
    - Normal requests (no JavaScript) get the full page with that group showing
      its first ``n`` pages of books.

    Only book details, statuses, ratings, and finished dates reach the
    template: never notes, the username, or the user's ID.
    """
    owner = get_object_or_404(get_user_model(), share_token=share_token)
    counts = status_counts(owner.shelf_entries.all())
    requested_group = request.GET.get("group", "")
    page = _parse_page(request.GET.get("page"))

    if is_htmx(request):
        ordering = dict(SHARED_GROUPS).get(requested_group)
        if ordering is None:
            raise Http404("No such group.")
        start = (page - 1) * SHARED_GROUP_SIZE
        group = _shared_group(owner, requested_group, ordering, counts, start, page)
        return render(request, "shelf/partials/shared_items.html", {"group": group})

    groups = []
    for status, ordering in SHARED_GROUPS:
        if counts.get(status):
            pages_shown = page if status == requested_group else 1
            groups.append(_shared_group(owner, status, ordering, counts, 0, pages_shown))

    context = {"display_name": owner.display_name, "groups": groups}
    response = render(request, "shelf/shared_shelf.html", context)
    patch_vary_headers(response, ["HX-Request"])
    return response


def _shared_group(
    owner: AbstractBaseUser,
    status: str,
    ordering: tuple[object, ...],
    counts: dict[str, int],
    start: int,
    pages_shown: int,
) -> dict[str, object]:
    """Return one group of the shared shelf: its books from ``start`` up to page ``pages_shown``.

    ``next_page`` is the page "Show more" should ask for, or ``None`` when
    every book in the group is already shown.
    """
    stop = pages_shown * SHARED_GROUP_SIZE
    entries = owner.shelf_entries.filter(status=status).select_related("book").order_by(*ordering)
    total = counts.get(status, 0)
    return {
        "status": status,
        "label": ShelfEntry.Status(status).label,
        "total": total,
        "entries": list(entries[start:stop]),
        "next_page": pages_shown + 1 if total > stop else None,
    }


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
