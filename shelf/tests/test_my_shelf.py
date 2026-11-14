"""Tests for the My Shelf page and the logged-in navigation."""

import datetime

import pytest

from shelf import openlibrary
from shelf.models import Book, ShelfEntry


def test_logged_in_user_visiting_home_goes_to_my_shelf(logged_in_client):
    response = logged_in_client.get("/")

    assert response.status_code == 302
    assert response.url == "/shelf/"


def test_empty_shelf_explains_itself_and_links_to_search(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-empty-shelf" in html
    assert "Your shelf is empty" in html
    assert 'href="/search/"' in html


def test_navbar_shows_app_links_and_user_menu_when_logged_in(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert 'href="/search/"' in html
    assert 'href="/shelf/"' in html
    assert 'href="/accounts/profile/"' in html
    # Log out is a POST form, not a link.
    assert 'method="post" action="/accounts/logout/"' in html
    assert "reader" in html
    # The logged-out buttons are gone.
    assert 'href="/accounts/signup/"' not in html


def test_navbar_marks_the_current_page(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert 'href="/shelf/" class="btn btn-neutral" aria-current="page"' in html
    assert 'href="/search/" class="btn btn-ghost"' in html


def test_navbar_shows_signup_and_login_when_logged_out(client):
    html = client.get("/").content.decode()

    assert 'href="/accounts/signup/"' in html
    assert 'href="/accounts/login/"' in html
    assert "/accounts/logout/" not in html


# --- Listing saved books -------------------------------------------------------


def add_to_shelf(user, key: str, title: str, **entry_fields) -> ShelfEntry:
    """Put a book with work key ``key`` on ``user``'s shelf."""
    book, _ = Book.objects.get_or_create(
        ol_work_key=key,
        defaults={"title": title, "authors": "Some Author", "first_publish_year": 2001},
    )
    return ShelfEntry.objects.create(user=user, book=book, **entry_fields)


@pytest.fixture
def reader(logged_in_client, django_user_model):
    """The user that ``logged_in_client`` is logged in as."""
    return django_user_model.objects.get(username="reader")


def test_saved_books_are_listed_as_rows_with_their_details(logged_in_client, reader):
    add_to_shelf(
        reader,
        "OL1W",
        "The Hobbit",
        status=ShelfEntry.Status.FINISHED,
        rating=4,
        finished_on=datetime.date(2026, 3, 14),
    )

    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-empty-shelf" not in html
    assert html.count("data-book-row") == 1
    assert "The Hobbit" in html
    assert "Some Author" in html
    assert "2001" in html
    assert 'data-status="finished"' in html
    assert ">Finished<" in html
    assert 'data-rating="4"' in html
    assert "Finished Mar 14, 2026" in html
    assert "Added " in html
    assert "0 notes" in html


def test_unrated_books_say_not_rated(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Circe")

    html = logged_in_client.get("/shelf/").content.decode()

    assert "Not rated" in html
    assert ">To Be Read<" in html


def test_newest_additions_come_first(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "First Saved")
    add_to_shelf(reader, "OL2W", "Second Saved")

    html = logged_in_client.get("/shelf/").content.decode()

    assert html.index("Second Saved") < html.index("First Saved")


def test_only_the_users_own_books_are_listed(logged_in_client, reader, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    add_to_shelf(reader, "OL1W", "Mine")
    add_to_shelf(other, "OL2W", "Not Mine")

    html = logged_in_client.get("/shelf/").content.decode()

    assert "Mine" in html
    assert "Not Mine" not in html


def test_shelf_works_while_open_library_is_down(logged_in_client, reader, monkeypatch):
    def open_library_is_down(*args: object, **kwargs: object) -> None:
        raise openlibrary.OpenLibraryUnavailable("down")

    monkeypatch.setattr(openlibrary, "search", open_library_is_down)
    monkeypatch.setattr(openlibrary, "get_work", open_library_is_down)
    add_to_shelf(reader, "OL1W", "The Hobbit")

    response = logged_in_client.get("/shelf/")

    assert response.status_code == 200
    assert "The Hobbit" in response.content.decode()
