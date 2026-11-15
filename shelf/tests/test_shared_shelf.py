"""Tests for the public, read-only shared shelf page (/shared/<token>/)."""

import datetime

import pytest

from accounts.models import new_share_token
from shelf.models import Note, ShelfEntry
from shelf.tests.helpers import add_to_shelf

# --- Behavior 1: notes and the username are never shown ------------------------


def test_shared_page_shows_the_books_but_never_notes_or_the_username(client, django_user_model):
    owner = django_user_model.objects.create_user(
        username="secret_owner_name", password="pw-12345-long", share_token=new_share_token()
    )
    entry = add_to_shelf(owner, status=ShelfEntry.Status.FINISHED, rating=4)
    Note.objects.create(entry=entry, text="A very private thought about Bilbo")

    # A visitor who isn't logged in opens the link.
    response = client.get(f"/shared/{owner.share_token}/")

    assert response.status_code == 200
    page = response.content.decode()
    # The shelf itself is shown...
    assert "The Hobbit" in page
    assert "J.R.R. Tolkien" in page
    # ...but nothing private: no note text, no username, no user ID in any link.
    assert "A very private thought about Bilbo" not in page
    assert "secret_owner_name" not in page
    assert f"/users/{owner.pk}" not in page


# --- Finding the shelf -----------------------------------------------------------

# HTMX adds this header to every request it sends.
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def sharer(django_user_model):
    """A user with sharing turned on and no display name."""
    return django_user_model.objects.create_user(
        username="sharer", password="pw-12345-long", share_token=new_share_token()
    )


def shared_url(user) -> str:
    """Return the shared-shelf path for ``user``'s current share token."""
    return f"/shared/{user.share_token}/"


def test_unknown_token_is_not_found(client, sharer):
    assert client.get("/shared/not-a-real-token/").status_code == 404


def test_shared_page_has_no_forms_or_edit_controls(client, sharer):
    add_to_shelf(sharer, rating=5)

    page = client.get(shared_url(sharer)).content.decode()

    assert "<form" not in page
    assert "<button" not in page
    assert "/shelf/" not in page  # No links to the owner's private book pages.


def test_shared_page_asks_search_engines_not_to_index_it(client, sharer):
    page = client.get(shared_url(sharer)).content.decode()

    assert '<meta name="robots" content="noindex, nofollow">' in page


# --- Heading ---------------------------------------------------------------------


def test_heading_is_the_display_name_when_set(client, sharer):
    sharer.display_name = "Maya"
    sharer.save()

    response = client.get(shared_url(sharer))

    assert "Maya" in response.content.decode()
    assert "<title>Maya · Shared bookshelf" in response.content.decode()


def test_heading_says_a_shared_bookshelf_without_a_display_name(client, sharer):
    page = client.get(shared_url(sharer)).content.decode()

    assert "<h1" in page
    assert "A shared bookshelf</h1>" in page


def test_empty_shelf_shows_a_friendly_message(client, sharer):
    page = client.get(shared_url(sharer)).content.decode()

    assert "data-shared-empty" in page
    assert "data-shared-group" not in page


# --- Groups and their order ---------------------------------------------------------


def test_groups_appear_in_order_and_empty_groups_are_hidden(client, sharer):
    add_to_shelf(sharer, "OL1W", "A TBR book", status=ShelfEntry.Status.TO_BE_READ)
    add_to_shelf(sharer, "OL2W", "A finished book", status=ShelfEntry.Status.FINISHED)
    add_to_shelf(sharer, "OL3W", "A current book", status=ShelfEntry.Status.READING)
    # No Did Not Finish books, so that group isn't shown.

    response = client.get(shared_url(sharer))

    groups = [group["status"] for group in response.context["groups"]]
    assert groups == ["reading", "finished", "tbr"]
    page = response.content.decode()
    assert page.index("A current book") < page.index("A finished book") < page.index("A TBR book")
    assert "Did Not Finish" not in page


def test_finished_books_are_most_recently_finished_first_with_undated_last(client, sharer):
    today = datetime.date.today()
    finished = ShelfEntry.Status.FINISHED
    long_ago = datetime.date(2020, 1, 1)
    add_to_shelf(sharer, "OL1W", "Long ago", status=finished, finished_on=long_ago)
    add_to_shelf(sharer, "OL2W", "No date", status=finished)
    add_to_shelf(sharer, "OL3W", "Recently", status=finished, finished_on=today)

    response = client.get(shared_url(sharer))

    (group,) = response.context["groups"]
    assert [entry.book.title for entry in group["entries"]] == ["Recently", "Long ago", "No date"]


def test_each_book_shows_its_stars_and_finished_date(client, sharer):
    add_to_shelf(
        sharer,
        status=ShelfEntry.Status.FINISHED,
        rating=4,
        finished_on=datetime.date(2026, 3, 5),
    )

    page = client.get(shared_url(sharer)).content.decode()

    assert 'data-rating="4"' in page
    assert "Finished Mar 5, 2026" in page


# --- Show more ------------------------------------------------------------------


def fill_group(user, count: int, status: str = ShelfEntry.Status.TO_BE_READ) -> None:
    """Put ``count`` books with ``status`` on ``user``'s shelf, titled "Book 1", "Book 2", ..."""
    for number in range(1, count + 1):
        add_to_shelf(user, f"OL{number}W", f"Book {number}", status=status)


def test_each_group_shows_twelve_books_then_a_show_more_link(client, sharer):
    fill_group(sharer, 13)

    response = client.get(shared_url(sharer))

    (group,) = response.context["groups"]
    assert group["total"] == 13
    assert len(group["entries"]) == 12
    assert group["next_page"] == 2
    assert "?group=tbr&amp;page=2" in response.content.decode()


def test_no_show_more_when_the_whole_group_fits(client, sharer):
    fill_group(sharer, 12)

    page = client.get(shared_url(sharer)).content.decode()

    assert "data-show-more" not in page


def test_show_more_with_htmx_returns_only_the_next_books(client, sharer):
    fill_group(sharer, 26)

    response = client.get(shared_url(sharer), {"group": "tbr", "page": "2"}, **HTMX)

    page = response.content.decode()
    assert "<html" not in page  # Just the new items, not a full page.
    assert page.count("data-shared-book") == 12
    # Newest added first, so page 2 holds books 14 down to 3.
    assert "Book 14<" in page and "Book 3<" in page
    assert "Book 15<" not in page and "Book 2<" not in page
    # Two books are left, so there's another "Show more" for page 3.
    assert "?group=tbr&amp;page=3" in page


def test_last_show_more_has_no_further_link(client, sharer):
    fill_group(sharer, 13)

    page = client.get(shared_url(sharer), {"group": "tbr", "page": "2"}, **HTMX).content.decode()

    assert page.count("data-shared-book") == 1
    assert "data-show-more" not in page


def test_show_more_for_an_unknown_group_is_not_found(client, sharer):
    response = client.get(shared_url(sharer), {"group": "secrets", "page": "2"}, **HTMX)

    assert response.status_code == 404


def test_show_more_without_javascript_expands_that_group_on_the_full_page(client, sharer):
    fill_group(sharer, 30)
    add_to_shelf(sharer, "OL99W", "Current read", status=ShelfEntry.Status.READING)

    response = client.get(shared_url(sharer), {"group": "tbr", "page": "2"})

    groups = {group["status"]: group for group in response.context["groups"]}
    assert len(groups["tbr"]["entries"]) == 24
    assert groups["tbr"]["next_page"] == 3
    assert len(groups["reading"]["entries"]) == 1
