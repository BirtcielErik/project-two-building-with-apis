"""Tests for the shelf entries API (``/api/entries/``): reading, creating, updating, deleting."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from shelf import openlibrary
from shelf.models import Book, Note, ShelfEntry
from shelf.tests.helpers import add_to_shelf


@pytest.fixture
def token_client(reader) -> APIClient:
    """An API client that sends ``reader``'s token in the Authorization header."""
    token, _ = Token.objects.get_or_create(user=reader)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


# --- Behavior 1: a token sees only its owner's shelf -------------------------------


def test_a_token_lists_only_its_owners_entries_and_404s_on_others(
    token_client, reader, django_user_model
):
    mine = add_to_shelf(reader, "OL27482W", "The Hobbit")
    other_user = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    theirs = add_to_shelf(other_user, "OL893415W", "Dune", "Frank Herbert")

    listing = token_client.get("/api/entries/")

    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["results"]] == [mine.pk]
    # Their entry is "not found", never "forbidden", so its ID can't be discovered.
    assert token_client.get(f"/api/entries/{theirs.pk}/").status_code == 404
    assert token_client.get(f"/api/entries/{mine.pk}/").status_code == 200


# --- Authentication ------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/api/entries/", "/api/entries/1/"])
def test_requests_without_a_valid_token_or_session_get_401(url):
    client = APIClient()
    assert client.get(url).status_code == 401

    client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
    assert client.get(url).status_code == 401


def test_a_logged_in_browser_session_can_use_the_api(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.get("/api/entries/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [entry.pk]


# --- One entry -------------------------------------------------------------------------


def test_retrieve_nests_the_book_with_a_ready_made_cover_url(token_client, reader):
    entry = add_to_shelf(
        reader, "OL27482W", "The Hobbit", status=ShelfEntry.Status.FINISHED, rating=5
    )
    Book.objects.filter(pk=entry.book.pk).update(cover_id=14627509)

    data = token_client.get(f"/api/entries/{entry.pk}/").json()

    assert data["status"] == "finished"
    assert data["rating"] == 5
    assert data["finished_on"] is None
    assert data["book"] == {
        "work_key": "OL27482W",
        "title": "The Hobbit",
        "authors": "J.R.R. Tolkien",
        "first_publish_year": 1937,
        # default=false: a missing image is a 404, not a blank 1×1 picture.
        "cover_url": "https://covers.openlibrary.org/b/id/14627509-M.jpg?default=false",
    }
    assert {"id", "added_at", "updated_at"} <= data.keys()


def test_cover_url_is_null_when_the_book_has_no_cover(token_client, reader):
    entry = add_to_shelf(reader)

    data = token_client.get(f"/api/entries/{entry.pk}/").json()

    assert data["book"]["cover_url"] is None


# --- Listing: same parameters and results as My Shelf ----------------------------


@pytest.fixture
def varied_shelf(reader) -> None:
    """A shelf of 15 books with a mix of statuses, ratings, and finished dates.

    15 is more than one page (12), so the parity tests also cover page 2.
    """
    Status = ShelfEntry.Status
    statuses = [Status.TO_BE_READ, Status.READING, Status.FINISHED, Status.DID_NOT_FINISH]
    for n in range(15):
        add_to_shelf(
            reader,
            f"OL{n + 1}W",
            f"Book {chr(ord('A') + n)}",
            "Ann Author" if n % 2 else "Zed Writer",
            status=statuses[n % 4],
            rating=(n % 5) + 1 if n % 3 else None,
            finished_on=datetime.date(2026, 1, n + 1) if n % 4 == 2 else None,
        )


PARITY_QUERIES = [
    {},
    {"page": "2"},
    {"q": "zed"},
    {"status": "finished"},
    {"min_rating": "3"},
    {"rated": "no"},
    {"rated": "yes", "ordering": "-rating"},
    {"ordering": "title"},
    {"ordering": "-author"},
    {"ordering": "finished"},
    {"ordering": "-updated", "page": "2"},
    {"q": "book", "status": "tbr", "min_rating": "1", "ordering": "added"},
]


@pytest.mark.parametrize("params", PARITY_QUERIES)
def test_api_list_matches_my_shelf_for_the_same_parameters(
    varied_shelf, logged_in_client, token_client, params
):
    website = logged_in_client.get("/shelf/", params)
    api = token_client.get("/api/entries/", params).json()

    website_ids = [entry.pk for entry in website.context["page_obj"]]
    assert [item["id"] for item in api["results"]] == website_ids
    assert api["count"] == website.context["page_obj"].paginator.count


def test_api_list_pages_at_12_with_links(varied_shelf, token_client):
    first = token_client.get("/api/entries/").json()
    second = token_client.get("/api/entries/", {"page": 2}).json()

    assert first["count"] == 15
    assert len(first["results"]) == 12 and len(second["results"]) == 3
    assert first["previous"] is None and first["next"].endswith("/api/entries/?page=2")
    assert second["next"] is None


@pytest.mark.parametrize(
    "params", [{"status": "lost"}, {"min_rating": "9"}, {"rated": "maybe"}, {"ordering": "pk"}]
)
def test_api_list_rejects_invalid_filter_values_with_400(token_client, params):
    response = token_client.get("/api/entries/", params)

    assert response.status_code == 400
    assert set(params) <= response.json().keys()


def test_api_list_page_past_the_end_is_404(token_client, reader):
    add_to_shelf(reader)

    assert token_client.get("/api/entries/", {"page": 2}).status_code == 404


def test_the_api_never_calls_open_library(token_client, reader, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("The read API must not call Open Library.")

    monkeypatch.setattr(openlibrary, "search", fail)
    monkeypatch.setattr(openlibrary, "get_work", fail)
    entry = add_to_shelf(reader)

    assert token_client.get("/api/entries/").status_code == 200
    assert token_client.get(f"/api/entries/{entry.pk}/").status_code == 200


# --- Creating entries ----------------------------------------------------------------

DUNE = openlibrary.SearchResult(
    work_key="OL893415W",
    title="Dune",
    authors=["Frank Herbert"],
    first_publish_year=1965,
    cover_id=11481354,
)


@pytest.fixture
def get_work_calls(monkeypatch) -> list[str]:
    """Make ``openlibrary.get_work`` return Dune; return the list of keys it was asked for."""
    calls: list[str] = []

    def fake_get_work(work_key: str) -> openlibrary.SearchResult:
        calls.append(work_key)
        return DUNE

    monkeypatch.setattr(openlibrary, "get_work", fake_get_work)
    return calls


# --- Behavior 1: create takes a work key; the server supplies the book details --------


def test_create_looks_up_the_book_itself_and_saves_it_to_the_callers_shelf(
    token_client, reader, django_user_model, get_work_calls
):
    other_user = django_user_model.objects.create_user(username="other", password="pw-12345-long")

    response = token_client.post(
        "/api/entries/",
        {
            "work_key": "OL893415W",
            "status": "finished",
            "rating": 4,
            "finished_on": "2026-02-01",
            # Attempts to fake shared book data or save to someone else's shelf:
            "user": other_user.pk,
            "book": {"title": "Fake Title", "authors": "Nobody"},
            "title": "Fake Title",
        },
        format="json",
    )

    assert response.status_code == 201
    assert get_work_calls == ["OL893415W"]
    entry = ShelfEntry.objects.get()
    assert entry.user == reader  # always the caller, whatever the body says
    assert (entry.status, entry.rating, entry.finished_on) == (
        "finished",
        4,
        datetime.date(2026, 2, 1),
    )
    book = entry.book
    assert (book.ol_work_key, book.title, book.authors, book.first_publish_year, book.cover_id) == (
        "OL893415W",
        "Dune",
        "Frank Herbert",
        1965,
        11481354,
    )
    data = response.json()
    assert data["id"] == entry.pk
    assert data["book"]["title"] == "Dune"
    assert data["book"]["work_key"] == "OL893415W"


# --- Behavior 2: Open Library failures map to 503 / 502 --------------------------------


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (openlibrary.OpenLibraryUnavailable("Open Library did not respond."), 503),
        (openlibrary.OpenLibraryBadResponse("Open Library returned invalid JSON."), 502),
    ],
)
def test_open_library_failures_on_create_return_503_or_502_and_save_nothing(
    token_client, monkeypatch, error, expected_status
):
    def failing_get_work(work_key: str) -> openlibrary.SearchResult:
        raise error

    monkeypatch.setattr(openlibrary, "get_work", failing_get_work)
    # Return a crash as a 500 response (what a real client would see) instead of
    # re-raising it inside the test.
    token_client.raise_request_exception = False

    response = token_client.post("/api/entries/", {"work_key": "OL893415W"}, format="json")

    assert response.status_code == expected_status
    assert "detail" in response.json()  # a readable message, not an HTML error page
    assert not Book.objects.exists()
    assert not ShelfEntry.objects.exists()


# --- Behavior 3: an entry can't be pointed at a different book -------------------------


@pytest.mark.parametrize("method", ["put", "patch"])
def test_sending_a_work_key_on_update_is_a_400_and_changes_nothing(token_client, reader, method):
    entry = add_to_shelf(reader, "OL27482W", "The Hobbit")
    add_to_shelf(reader, "OL893415W", "Dune", "Frank Herbert")  # another book that exists
    send = getattr(token_client, method)

    response = send(
        f"/api/entries/{entry.pk}/",
        {"work_key": "OL893415W", "status": "finished", "rating": 5},
        format="json",
    )

    assert response.status_code == 400
    assert "work_key" in response.json()  # the error names the offending field
    entry.refresh_from_db()
    assert entry.book.ol_work_key == "OL27482W"
    # The whole request is rejected, so the other fields weren't saved either.
    assert (entry.status, entry.rating) == ("tbr", None)


# --- Create: bad requests -----------------------------------------------------------


@pytest.mark.parametrize(
    "work_key",
    ["hobbit", "OL27482M", "/works/OL27482W", "OL27482W title:x", "OL27482W"],
)
def test_bad_format_and_duplicate_keys_are_400_without_calling_open_library(
    token_client, reader, get_work_calls, work_key
):
    add_to_shelf(reader, "OL27482W", "The Hobbit")  # makes "OL27482W" a duplicate

    response = token_client.post("/api/entries/", {"work_key": work_key}, format="json")

    assert response.status_code == 400
    assert "work_key" in response.json()
    assert get_work_calls == []  # no outbound request
    assert ShelfEntry.objects.count() == 1


@pytest.mark.parametrize("body", [{}, {"work_key": ""}])
def test_a_missing_work_key_is_400(token_client, get_work_calls, body):
    response = token_client.post("/api/entries/", body, format="json")

    assert response.status_code == 400
    assert "work_key" in response.json()
    assert get_work_calls == []


def test_an_unknown_key_is_400_and_stores_nothing(token_client, monkeypatch):
    def not_found(work_key: str) -> openlibrary.SearchResult:
        raise openlibrary.OpenLibraryNotFound(work_key)

    monkeypatch.setattr(openlibrary, "get_work", not_found)

    response = token_client.post("/api/entries/", {"work_key": "OL999999999W"}, format="json")

    assert response.status_code == 400
    assert response.json()["work_key"] == ["Open Library has no book with that key."]
    assert not Book.objects.exists()
    assert not ShelfEntry.objects.exists()


def test_create_defaults_to_to_be_read(token_client, get_work_calls):
    response = token_client.post("/api/entries/", {"work_key": "OL893415W"}, format="json")

    assert response.status_code == 201
    data = response.json()
    assert (data["status"], data["rating"], data["finished_on"]) == ("tbr", None, None)
    assert "work_key" not in data  # write-only: it's shown inside "book" instead


def test_a_known_book_can_be_added_while_open_library_is_down(
    token_client, django_user_model, monkeypatch
):
    other_user = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    add_to_shelf(other_user, "OL893415W", "Dune", "Frank Herbert")

    def open_library_is_down(work_key: str) -> openlibrary.SearchResult:
        raise openlibrary.OpenLibraryUnavailable("down")

    monkeypatch.setattr(openlibrary, "get_work", open_library_is_down)

    response = token_client.post("/api/entries/", {"work_key": "OL893415W"}, format="json")

    assert response.status_code == 201
    assert Book.objects.count() == 1  # the existing Book was reused


# --- Validation: same rules as the website form -------------------------------------


def _tomorrow() -> str:
    """Return tomorrow's date (in the site's time zone) as ``YYYY-MM-DD``."""
    return (timezone.localdate() + datetime.timedelta(days=1)).isoformat()


# Each invalid value and the field its error is reported on. "TOMORROW" is
# swapped for tomorrow's real date when the test runs (see `_with_dates`).
INVALID_DETAILS = [
    ({"rating": 0}, "rating"),
    ({"rating": 6}, "rating"),
    ({"status": "reread"}, "status"),
    ({"finished_on": "TOMORROW"}, "finished_on"),
]


def _with_dates(details: dict) -> dict:
    """Return ``details`` with any ``"TOMORROW"`` value replaced by tomorrow's date."""
    return {key: _tomorrow() if value == "TOMORROW" else value for key, value in details.items()}


@pytest.mark.parametrize(("details", "field"), INVALID_DETAILS)
def test_invalid_details_on_create_are_400_without_calling_open_library(
    token_client, get_work_calls, details, field
):
    response = token_client.post(
        "/api/entries/", {"work_key": "OL893415W", **_with_dates(details)}, format="json"
    )

    assert response.status_code == 400
    assert field in response.json()
    assert get_work_calls == []
    assert not ShelfEntry.objects.exists()


@pytest.mark.parametrize(("details", "field"), INVALID_DETAILS)
def test_invalid_details_on_update_are_400_and_change_nothing(token_client, reader, details, field):
    entry = add_to_shelf(reader)

    response = token_client.patch(f"/api/entries/{entry.pk}/", _with_dates(details), format="json")

    assert response.status_code == 400
    assert field in response.json()
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.finished_on) == ("tbr", None, None)


def test_future_date_error_message_matches_the_website(token_client, reader):
    entry = add_to_shelf(reader)

    response = token_client.patch(
        f"/api/entries/{entry.pk}/", {"finished_on": _tomorrow()}, format="json"
    )

    assert response.json()["finished_on"] == ["The finished date can't be in the future."]


# --- Updating ------------------------------------------------------------------------


def test_put_replaces_status_rating_and_finished_date(token_client, reader):
    entry = add_to_shelf(reader, rating=3, finished_on=datetime.date(2026, 1, 5))

    response = token_client.put(
        f"/api/entries/{entry.pk}/",
        {"status": "dnf", "rating": 2, "finished_on": "2026-03-14"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["book"]["work_key"] == "OL27482W"
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.finished_on) == (
        "dnf",  # a rating is allowed at any status, even Did Not Finish
        2,
        datetime.date(2026, 3, 14),
    )


def test_patch_changes_only_the_fields_sent_and_can_clear_a_rating(token_client, reader):
    entry = add_to_shelf(
        reader, status=ShelfEntry.Status.FINISHED, rating=4, finished_on=datetime.date(2026, 1, 5)
    )

    response = token_client.patch(f"/api/entries/{entry.pk}/", {"rating": None}, format="json")

    assert response.status_code == 200
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.finished_on) == (
        "finished",
        None,
        datetime.date(2026, 1, 5),
    )


def test_updates_never_call_open_library(token_client, reader, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Updating an entry must not call Open Library.")

    monkeypatch.setattr(openlibrary, "get_work", fail)
    entry = add_to_shelf(reader)

    response = token_client.patch(f"/api/entries/{entry.pk}/", {"status": "reading"}, format="json")

    assert response.status_code == 200


# --- Deleting ------------------------------------------------------------------------


def test_delete_removes_the_entry_and_its_notes_but_keeps_the_book(token_client, reader):
    entry = add_to_shelf(reader)
    Note.objects.create(entry=entry, text="Second breakfast!")

    response = token_client.delete(f"/api/entries/{entry.pk}/")

    assert response.status_code == 204
    assert not ShelfEntry.objects.exists()
    assert not Note.objects.exists()
    assert Book.objects.filter(ol_work_key="OL27482W").exists()  # Books are a local cache


# --- Ownership and authentication on writes --------------------------------------


@pytest.mark.parametrize(
    ("method", "body"),
    [
        ("get", None),
        ("put", {"status": "dnf", "rating": 1, "finished_on": None}),
        ("patch", {"rating": 1}),
        ("delete", None),
    ],
)
def test_every_method_on_another_users_entry_is_404_and_changes_nothing(
    token_client, django_user_model, method, body
):
    other_user = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    theirs = add_to_shelf(other_user, status=ShelfEntry.Status.READING, rating=5)
    Note.objects.create(entry=theirs, text="Private thought")

    response = getattr(token_client, method)(f"/api/entries/{theirs.pk}/", body, format="json")

    assert response.status_code == 404
    theirs.refresh_from_db()  # still exists
    assert (theirs.status, theirs.rating) == ("reading", 5)
    assert theirs.notes.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/entries/"),
        ("put", "/api/entries/1/"),
        ("patch", "/api/entries/1/"),
        ("delete", "/api/entries/1/"),
    ],
)
def test_writes_without_a_token_or_session_get_401(method, url):
    response = getattr(APIClient(), method)(url, {"status": "tbr"}, format="json")

    assert response.status_code == 401
