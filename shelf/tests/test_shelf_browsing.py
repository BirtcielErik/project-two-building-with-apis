"""Tests for browsing My Shelf: search, filters, sorting, pagination, and the strip."""

import re

import pytest

from shelf.models import ShelfEntry
from shelf.tests.helpers import add_to_shelf

Status = ShelfEntry.Status


def listed_titles(html: str) -> list[str]:
    """Return the titles of the list rows on a My Shelf page, in order."""
    headings = re.findall(r"data-book-row.*?<h3[^>]*>(.*?)</h3>", html, re.DOTALL)
    # The title is wrapped in a link to the detail page, so keep only its text.
    return [re.sub(r"<[^>]+>", "", heading).strip() for heading in headings]


def status_counts(html: str) -> dict[str, int]:
    """Return the sidebar's book count for each status ("all" for All books)."""
    return {
        status: int(count)
        for status, count in re.findall(r'data-status-count="(\w+)">(\d*)<', html)
        if count
    }


def test_filters_combine_while_status_counts_cover_the_whole_shelf(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune", "Frank Herbert", status=Status.FINISHED, rating=5)
    add_to_shelf(reader, "OL2W", "Dune Messiah", "Frank Herbert", status=Status.FINISHED, rating=3)
    add_to_shelf(
        reader, "OL3W", "Children of Dune", "Frank Herbert", status=Status.READING, rating=5
    )
    add_to_shelf(reader, "OL4W", "Emma", "Jane Austen", status=Status.FINISHED, rating=5)
    add_to_shelf(reader, "OL5W", "Persuasion", "Jane Austen")  # To Be Read, unrated

    html = logged_in_client.get(
        "/shelf/", {"q": "herbert", "status": "finished", "min_rating": "4"}
    ).content.decode()

    # Only Dune matches all three: by Herbert, Finished, and rated 4 or more.
    assert listed_titles(html) == ["Dune"]
    # The sidebar counts ignore the filters: they describe the whole shelf.
    assert status_counts(html) == {"all": 5, "tbr": 1, "reading": 1, "finished": 3, "dnf": 0}


HTMX = {"HTTP_HX_REQUEST": "true"}


def fill_shelf(user, count: int) -> None:
    """Add ``count`` books titled "Book 01", "Book 02", … (the last one is newest)."""
    for number in range(1, count + 1):
        add_to_shelf(user, f"OL{number}W", f"Book {number:02}")


# --- Pagination ----------------------------------------------------------------


def test_shelf_shows_twelve_books_per_page_with_the_range(logged_in_client, reader):
    fill_shelf(reader, 30)

    html = logged_in_client.get("/shelf/").content.decode()

    assert len(listed_titles(html)) == 12
    assert "Showing 1–12 of 30" in html
    assert 'aria-label="Pagination"' in html


def test_second_page_shows_the_next_twelve(logged_in_client, reader):
    fill_shelf(reader, 30)

    html = logged_in_client.get("/shelf/", {"page": "2"}).content.decode()

    assert "Showing 13–24 of 30" in html
    # Newest first: page 2 starts at the 13th newest book.
    assert listed_titles(html)[0] == "Book 18"


def test_page_links_keep_the_filters(logged_in_client, reader):
    for number in range(1, 15):
        add_to_shelf(reader, f"OL{number}W", f"Book {number:02}", status=Status.FINISHED)

    html = logged_in_client.get("/shelf/", {"status": "finished"}).content.decode()

    assert 'href="/shelf/?status=finished&amp;page=2"' in html


def test_page_past_the_end_shows_the_last_page(logged_in_client, reader):
    fill_shelf(reader, 14)

    html = logged_in_client.get("/shelf/", {"page": "99"}).content.decode()

    assert "Showing 13–14 of 14" in html


def test_one_page_of_books_has_no_pagination(logged_in_client, reader):
    fill_shelf(reader, 12)

    html = logged_in_client.get("/shelf/").content.decode()

    assert "Showing 1–12 of 12" in html
    assert 'aria-label="Pagination"' not in html


# --- Currently Reading strip ---------------------------------------------------


def reading_strip(html: str) -> str:
    """Return the part of a My Shelf page that holds the Currently Reading strip."""
    return html[html.index("data-reading-strip") : html.index('id="shelf-filters"')]


def test_reading_strip_shows_only_books_being_read(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "In Progress", status=Status.READING)
    add_to_shelf(reader, "OL2W", "Someday")

    strip = reading_strip(logged_in_client.get("/shelf/").content.decode())

    assert "In Progress" in strip
    assert "Someday" not in strip


@pytest.mark.parametrize(
    "params",
    [
        {"q": "someday"},
        {"status": "tbr"},
        {"min_rating": "5"},
        {"rated": "yes"},
        {"ordering": "title"},
        {"page": "1"},
    ],
)
def test_reading_strip_stays_put_whatever_the_filters(logged_in_client, reader, params):
    """The strip doesn't jump in and out: filters change only the list below it."""
    add_to_shelf(reader, "OL1W", "In Progress", status=Status.READING)
    add_to_shelf(reader, "OL2W", "Someday", rating=5)

    html = logged_in_client.get("/shelf/", params).content.decode()

    assert "In Progress" in reading_strip(html)
    # Every one of these filters leaves "In Progress" out of the list itself.
    if params.keys() & {"q", "status", "min_rating", "rated"}:
        assert listed_titles(html) == ["Someday"]


def test_no_reading_strip_when_nothing_is_being_read(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Someday")

    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-reading-strip" not in html


# --- HTMX and bookmarkable URLs ------------------------------------------------


def test_htmx_request_gets_only_the_results(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "In Progress", status=Status.READING)

    html = logged_in_client.get("/shelf/", {"q": "progress"}, **HTMX).content.decode()

    assert "<html" not in html
    # The form (with its search box) and the strip stay on the page untouched.
    assert 'id="shelf-filters"' not in html
    assert "data-reading-strip" not in html
    assert "Showing 1–1 of 1" in html
    assert listed_titles(html) == ["In Progress"]


def test_bookmarked_url_shows_its_choices_selected(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune", status=Status.FINISHED, rating=5)
    params = {
        "q": "dune",
        "status": "finished",
        "min_rating": "4",
        "rated": "yes",
        "ordering": "-rating",
    }

    html = logged_in_client.get("/shelf/", params).content.decode()

    assert "<html" in html
    assert 'name="q" value="dune"' in html
    assert 'name="status" value="finished" class="sr-only" checked' in html
    assert 'name="min_rating" value="4" class="radio radio-xs radio-primary" checked' in html
    assert 'name="rated" value="yes" class="radio radio-xs radio-primary" checked' in html
    assert '<option value="-rating" selected>' in html
    assert listed_titles(html) == ["Dune"]


@pytest.mark.parametrize("url", ["/shelf/", "/search/"])
def test_back_button_reloads_from_the_server(logged_in_client, reader, url):
    """HTMX's saved copy of a page shows the controls as first loaded, not as changed.

    ``hx-history="false"`` makes Back re-request the URL instead, so the
    server renders that URL's filters (or search query) selected.
    """
    add_to_shelf(reader, "OL1W", "Dune")

    html = logged_in_client.get(url).content.decode()

    assert 'hx-history="false"' in html


def test_no_filters_selects_the_any_choices(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune")

    html = logged_in_client.get("/shelf/").content.decode()

    assert 'name="status" value="" class="sr-only" checked' in html
    assert 'name="min_rating" value="" class="radio radio-xs radio-primary" checked' in html
    assert 'name="rated" value="" class="radio radio-xs radio-primary" checked' in html
    assert '<option value="" selected>Recently added</option>' in html


def test_invalid_values_are_ignored_on_the_website(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune")

    response = logged_in_client.get(
        "/shelf/", {"status": "lost", "min_rating": "9", "ordering": "price", "page": "x"}
    )

    assert response.status_code == 200
    assert listed_titles(response.content.decode()) == ["Dune"]


# --- Empty states and privacy --------------------------------------------------


def test_no_matches_offers_to_clear_the_filters(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune")

    html = logged_in_client.get("/shelf/", {"q": "zzz"}).content.decode()

    assert "data-no-matches" in html
    assert "No books match these filters." in html
    assert 'class="btn btn-outline btn-sm" data-clear-filters>Clear filters</a>' in html
    # It's still the user's shelf, not the "empty shelf" welcome.
    assert "data-empty-shelf" not in html


def test_empty_shelf_has_no_filters(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-empty-shelf" in html
    assert 'id="shelf-filters"' not in html
    assert "data-toggle-filters" not in html


def test_filters_button_controls_the_sidebar(logged_in_client, reader):
    add_to_shelf(reader, "OL1W", "Dune")

    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-toggle-filters" in html
    assert 'aria-controls="shelf-sidebar"' in html
    assert '<aside id="shelf-sidebar" class="hidden lg:block' in html


def test_other_users_books_are_not_counted_or_listed(logged_in_client, reader, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    add_to_shelf(reader, "OL1W", "Mine")
    add_to_shelf(other, "OL2W", "Theirs", status=Status.READING)

    html = logged_in_client.get("/shelf/").content.decode()

    assert listed_titles(html) == ["Mine"]
    assert status_counts(html)["all"] == 1
    assert status_counts(html)["reading"] == 0
    assert "Theirs" not in html
