"""Tests for the read-only shelf entries API (``/api/entries/``)."""

import datetime

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from shelf import openlibrary
from shelf.models import Book, ShelfEntry
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
