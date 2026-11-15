"""Tests for the book detail page: viewing, editing, and removing a shelf entry."""

import datetime
import re

import pytest
from django.utils import timezone

from shelf import openlibrary
from shelf.models import Book, ShelfEntry

# HTMX adds this header to every request it sends.
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def reader(logged_in_client, django_user_model):
    """The user that ``logged_in_client`` is logged in as."""
    return django_user_model.objects.get(username="reader")


def add_to_shelf(user, key: str = "OL27482W", title: str = "The Hobbit", **fields) -> ShelfEntry:
    """Put a book on ``user``'s shelf and return the entry."""
    book, _ = Book.objects.get_or_create(
        ol_work_key=key,
        defaults={"title": title, "authors": "J.R.R. Tolkien", "first_publish_year": 1937},
    )
    return ShelfEntry.objects.create(user=user, book=book, **fields)


def checked(html: str, name: str, value: str) -> bool:
    """Return whether the page's ``name`` radio button with ``value`` is checked."""
    pattern = rf'<input type="radio" name="{name}" value="{value}"[^>]*\schecked>'
    return re.search(pattern, html) is not None


# --- Behavior 1: status, rating, and finished date save together ---------------


def test_status_rating_and_finished_date_save_together_and_rating_can_be_cleared(
    logged_in_client, reader
):
    entry = add_to_shelf(reader)
    url = f"/shelf/{entry.pk}/update/"

    # A rating is allowed at any status, even Did Not Finish.
    response = logged_in_client.post(
        url, {"status": "dnf", "rating": "2", "finished_on": "2026-03-14"}, **HTMX
    )

    assert response.status_code == 200
    assert "Saved ✓" in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == ShelfEntry.Status.DID_NOT_FINISH
    assert entry.rating == 2
    assert entry.finished_on == datetime.date(2026, 3, 14)

    # Clearing the rating sends an empty value, which removes it.
    logged_in_client.post(url, {"status": "dnf", "rating": "", "finished_on": "2026-03-14"}, **HTMX)

    entry.refresh_from_db()
    assert entry.rating is None
    assert entry.status == ShelfEntry.Status.DID_NOT_FINISH


# --- Behavior 2: a future finished date is rejected inline ---------------------


def test_future_finished_date_is_rejected_inline_and_nothing_is_saved(logged_in_client, reader):
    entry = add_to_shelf(reader, status=ShelfEntry.Status.READING)
    url = f"/shelf/{entry.pk}/update/"
    today = timezone.localdate()
    tomorrow = today + datetime.timedelta(days=1)

    response = logged_in_client.post(
        url, {"status": "finished", "rating": "5", "finished_on": tomorrow.isoformat()}, **HTMX
    )

    # HTMX only swaps 200 responses, so the error comes back as a 200.
    assert response.status_code == 200
    html = response.content.decode()
    assert "Saved ✓" not in html
    assert "data-field-error" in html
    assert "The finished date can&#x27;t be in the future." in html
    # None of the three fields were saved.
    entry.refresh_from_db()
    assert entry.status == ShelfEntry.Status.READING
    assert entry.rating is None
    assert entry.finished_on is None

    # Today is the latest date allowed.
    response = logged_in_client.post(
        url, {"status": "finished", "rating": "5", "finished_on": today.isoformat()}, **HTMX
    )

    assert "Saved ✓" in response.content.decode()
    entry.refresh_from_db()
    assert entry.finished_on == today


# --- Behavior 3: other users' entries are 404 ----------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", ""), ("post", "update/"), ("post", "remove/")],
    ids=["view", "update", "remove"],
)
def test_another_users_entry_is_not_found(logged_in_client, django_user_model, method, path):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    entry = add_to_shelf(other, status=ShelfEntry.Status.READING, rating=4)

    request = getattr(logged_in_client, method)
    response = request(f"/shelf/{entry.pk}/{path}", {"status": "dnf", "rating": "1"})

    # 404, not 403: a user can't even learn that the entry exists.
    assert response.status_code == 404
    # And the other user's entry is untouched.
    entry.refresh_from_db()
    assert entry.status == ShelfEntry.Status.READING
    assert entry.rating == 4


def test_another_users_entry_shows_the_themed_404_page(
    logged_in_client, django_user_model, settings
):
    settings.DEBUG = False  # Django only uses the custom 404 page when debug is off.
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    entry = add_to_shelf(other)

    response = logged_in_client.get(f"/shelf/{entry.pk}/")

    assert response.status_code == 404
    html = response.content.decode()
    assert "Page not found" in html
    assert "css/tailwind.css" in html  # our styled layout, not Django's plain page
    assert "The Hobbit" not in html  # nothing about the other user's book leaks


def test_a_missing_entry_is_not_found(logged_in_client):
    assert logged_in_client.get("/shelf/999/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "post"])
def test_anonymous_visitor_is_sent_to_login(client, django_user_model, method):
    owner = django_user_model.objects.create_user(username="owner", password="pw-12345-long")
    entry = add_to_shelf(owner)
    url = f"/shelf/{entry.pk}/" if method == "get" else f"/shelf/{entry.pk}/update/"

    response = getattr(client, method)(url)

    assert response.status_code == 302
    assert response.url == f"/accounts/login/?next={url}"


# --- The detail page -------------------------------------------------------------


def test_detail_page_shows_the_book_and_links_to_open_library(logged_in_client, reader):
    entry = add_to_shelf(reader)
    Book.objects.filter(pk=entry.book.pk).update(cover_id=14627509)

    response = logged_in_client.get(f"/shelf/{entry.pk}/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "<h1" in html and "The Hobbit" in html
    assert "J.R.R. Tolkien" in html
    assert "First published 1937" in html
    added = timezone.localtime(entry.added_at)
    assert f"On your shelf since {added:%b} {added.day}, {added:%Y}" in html
    assert 'href="https://openlibrary.org/works/OL27482W"' in html
    assert "14627509-L.jpg" in html  # the large cover


def test_detail_page_form_shows_the_saved_details(logged_in_client, reader):
    entry = add_to_shelf(
        reader,
        status=ShelfEntry.Status.FINISHED,
        rating=4,
        finished_on=datetime.date(2026, 3, 14),
    )

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    # One radio button per status, with short labels; the saved one is checked.
    for short in ("TBR", "Reading", "Finished", "DNF"):
        assert f'aria-label="{short}"' in html
    assert checked(html, "status", "finished")
    assert not checked(html, "status", "tbr")
    assert checked(html, "rating", "4")
    assert not checked(html, "rating", "")
    assert 'value="2026-03-14"' in html
    assert "data-clear-rating" in html


def test_finished_date_picker_stops_at_today(logged_in_client, reader):
    entry = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert f'max="{timezone.localdate().isoformat()}"' in html


def test_detail_page_works_while_open_library_is_down(logged_in_client, reader, monkeypatch):
    def open_library_is_down(*args: object, **kwargs: object) -> None:
        raise openlibrary.OpenLibraryUnavailable("down")

    monkeypatch.setattr(openlibrary, "search", open_library_is_down)
    monkeypatch.setattr(openlibrary, "get_work", open_library_is_down)
    entry = add_to_shelf(reader)

    assert logged_in_client.get(f"/shelf/{entry.pk}/").status_code == 200


# --- Saving without JavaScript ------------------------------------------------


def test_saving_without_htmx_returns_to_the_detail_page_with_a_toast(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(
        f"/shelf/{entry.pk}/update/", {"status": "reading", "rating": "3"}, follow=True
    )

    assert response.redirect_chain == [(f"/shelf/{entry.pk}/", 302)]
    assert "Saved your reading details." in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == ShelfEntry.Status.READING
    assert entry.rating == 3


def test_invalid_save_without_htmx_shows_the_full_page_with_errors(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/update/", {"status": "tbr", "rating": "9"})

    assert response.status_code == 200
    html = response.content.decode()
    assert "<h1" in html  # the whole page, not just the form
    assert "data-field-error" in html
    entry.refresh_from_db()
    assert entry.rating is None


@pytest.mark.parametrize("data", [{"status": "reread"}, {"status": "tbr", "rating": "0"}])
def test_invalid_status_or_rating_is_rejected_inline(logged_in_client, reader, data):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/update/", data, **HTMX)

    assert response.status_code == 200
    assert "data-field-error" in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == ShelfEntry.Status.TO_BE_READ
    assert entry.rating is None


# --- Removing a book --------------------------------------------------------------


def test_detail_page_has_a_confirmed_remove_button(logged_in_client, reader):
    entry = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert f'action="/shelf/{entry.pk}/remove/"' in html
    assert 'data-confirm-dialog="remove-dialog"' in html
    assert '<dialog id="remove-dialog"' in html
    assert "notes you wrote about it will be deleted too" in html


def test_removing_a_book_deletes_the_entry_and_returns_to_my_shelf(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/remove/", follow=True)

    assert response.redirect_chain == [("/shelf/", 302)]
    assert "Removed “The Hobbit” from your shelf." in response.content.decode()
    assert not ShelfEntry.objects.filter(pk=entry.pk).exists()
    # The shared Book row stays, as a local cache for the next person who saves it.
    assert Book.objects.filter(ol_work_key="OL27482W").exists()


@pytest.mark.parametrize("path", ["update/", "remove/"])
def test_changes_must_be_posted(logged_in_client, reader, path):
    entry = add_to_shelf(reader)

    response = logged_in_client.get(f"/shelf/{entry.pk}/{path}")

    assert response.status_code == 405
    assert ShelfEntry.objects.filter(pk=entry.pk).exists()


# --- Getting to the detail page -------------------------------------------------


def test_shelf_rows_and_reading_strip_link_to_the_detail_page(logged_in_client, reader):
    entry = add_to_shelf(reader, status=ShelfEntry.Status.READING)

    html = logged_in_client.get("/shelf/").content.decode()

    # Once in the list row and once in the Currently Reading strip.
    assert html.count(f'href="/shelf/{entry.pk}/"') == 2


def test_navbar_highlights_my_shelf_on_the_detail_page(logged_in_client, reader):
    entry = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert 'href="/shelf/" class="btn btn-neutral" aria-current="page"' in html
