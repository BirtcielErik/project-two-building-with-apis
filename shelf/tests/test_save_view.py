"""Tests for saving books from the Search page. Open Library is replaced with fakes."""

import pytest

from shelf import openlibrary
from shelf.models import Book, ShelfEntry

SAVE_URL = "/search/save/"
HTMX_HEADERS = {"HX-Request": "true"}

DUNE = openlibrary.SearchResult(
    work_key="OL893415W",
    title="Dune",
    authors=["Frank Herbert"],
    first_publish_year=1965,
    cover_id=11481354,
)


@pytest.fixture
def get_work_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Make ``openlibrary.get_work`` return Dune; return the list of keys it was asked for."""
    calls: list[str] = []

    def fake_get_work(work_key: str) -> openlibrary.SearchResult:
        calls.append(work_key)
        return DUNE

    monkeypatch.setattr(openlibrary, "get_work", fake_get_work)
    return calls


def fake_get_work_raising(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    """Make ``openlibrary.get_work`` fail with ``error``."""

    def fake_get_work(work_key: str) -> openlibrary.SearchResult:
        raise error

    monkeypatch.setattr(openlibrary, "get_work", fake_get_work)


def make_dune_book() -> Book:
    """Store Dune in the Book table, as if someone saved it before."""
    return Book.objects.create(ol_work_key="OL893415W", title="Dune", authors="Frank Herbert")


# --- Saving with HTMX --------------------------------------------------------


@pytest.mark.django_db
def test_save_adds_the_book_as_to_be_read_and_swaps_in_on_your_shelf(
    logged_in_client, get_work_calls
):
    response = logged_in_client.post(SAVE_URL, {"work_key": "OL893415W"}, headers=HTMX_HEADERS)

    entry = ShelfEntry.objects.get()
    assert entry.book.title == "Dune"
    assert entry.status == ShelfEntry.Status.TO_BE_READ
    html = response.content.decode()
    assert response.status_code == 200
    assert "data-on-shelf" in html
    assert f'href="/shelf/{entry.pk}/"' in html
    assert 'hx-post="/search/save/"' not in html  # the Save button is gone


@pytest.mark.django_db
def test_save_shows_a_toast_through_an_out_of_band_swap(logged_in_client, get_work_calls):
    html = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W"}, headers=HTMX_HEADERS
    ).content.decode()

    assert 'id="toasts"' in html
    assert 'hx-swap-oob="true"' in html
    assert "Saved “Dune” to your shelf as To Be Read." in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "label"),
    [("reading", "Currently Reading"), ("finished", "Finished"), ("dnf", "Did Not Finish")],
)
def test_the_menu_saves_with_another_status(logged_in_client, get_work_calls, status, label):
    html = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W", "status": status}, headers=HTMX_HEADERS
    ).content.decode()

    assert ShelfEntry.objects.get().status == status
    assert f"to your shelf as {label}." in html


@pytest.mark.django_db
def test_an_invalid_key_shows_an_inline_error_without_calling_open_library(
    logged_in_client, get_work_calls
):
    response = logged_in_client.post(SAVE_URL, {"work_key": "dune"}, headers=HTMX_HEADERS)

    html = response.content.decode()
    assert response.status_code == 200  # HTMX only swaps 2xx responses
    assert "data-save-error" in html
    assert "That isn&#x27;t a valid Open Library work key." in html
    assert 'hx-post="/search/save/"' in html  # the Save button stays, to try again
    assert get_work_calls == []
    assert not ShelfEntry.objects.exists()


@pytest.mark.django_db
def test_an_unknown_key_shows_a_not_found_error(logged_in_client, monkeypatch):
    fake_get_work_raising(monkeypatch, openlibrary.OpenLibraryNotFound("OL1W"))

    html = logged_in_client.post(
        SAVE_URL, {"work_key": "OL1W"}, headers=HTMX_HEADERS
    ).content.decode()

    assert "Open Library has no book with that key." in html
    assert not ShelfEntry.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (openlibrary.OpenLibraryUnavailable(), "Open Library isn&#x27;t responding right now."),
        (
            openlibrary.OpenLibraryBadResponse(),
            "Open Library sent back something we couldn&#x27;t read.",
        ),
    ],
)
def test_open_library_failures_show_an_inline_error(logged_in_client, monkeypatch, error, message):
    fake_get_work_raising(monkeypatch, error)

    response = logged_in_client.post(SAVE_URL, {"work_key": "OL1W"}, headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert message in response.content.decode()
    assert not ShelfEntry.objects.exists()


@pytest.mark.django_db
def test_a_known_book_saves_while_open_library_is_down(logged_in_client, monkeypatch):
    make_dune_book()
    fake_get_work_raising(monkeypatch, openlibrary.OpenLibraryUnavailable())

    html = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W"}, headers=HTMX_HEADERS
    ).content.decode()

    assert "data-on-shelf" in html
    assert ShelfEntry.objects.count() == 1


@pytest.mark.django_db
def test_saving_a_book_already_on_the_shelf_just_shows_on_your_shelf(
    logged_in_client, django_user_model, get_work_calls
):
    user = django_user_model.objects.get(username="reader")
    entry = ShelfEntry.objects.create(user=user, book=make_dune_book())

    html = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W"}, headers=HTMX_HEADERS
    ).content.decode()

    assert f'href="/shelf/{entry.pk}/"' in html
    assert "Saved “" not in html  # no success toast: nothing new was saved
    assert ShelfEntry.objects.count() == 1
    assert get_work_calls == []


@pytest.mark.django_db
def test_saving_only_touches_the_logged_in_users_shelf(
    logged_in_client, django_user_model, get_work_calls
):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    ShelfEntry.objects.create(user=other, book=make_dune_book())

    logged_in_client.post(SAVE_URL, {"work_key": "OL893415W"}, headers=HTMX_HEADERS)

    reader_entry = ShelfEntry.objects.get(user__username="reader")
    assert reader_entry.book.ol_work_key == "OL893415W"
    assert ShelfEntry.objects.filter(user=other).count() == 1
    assert get_work_calls == []  # the Book row was reused


# --- Without JavaScript, and protection --------------------------------------


@pytest.fixture
def fake_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``openlibrary.search`` return Dune, so following a redirect to Search works offline."""

    def search(query: str, page: int = 1) -> openlibrary.SearchPage:
        return openlibrary.SearchPage(query=query, page=page, total=1, results=[DUNE])

    monkeypatch.setattr(openlibrary, "search", search)


@pytest.mark.django_db
def test_without_htmx_saving_returns_to_the_search_page_with_a_message(
    logged_in_client, get_work_calls, fake_search
):
    response = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W", "next": "/search/?q=dune"}, follow=True
    )

    html = response.content.decode()
    assert response.redirect_chain[-1] == ("/search/?q=dune", 302)
    assert "Saved “Dune” to your shelf" in html
    assert "data-on-shelf" in html  # the result now shows as saved


@pytest.mark.django_db
def test_without_htmx_a_failed_save_shows_the_error_as_a_message(
    logged_in_client, get_work_calls, fake_search
):
    response = logged_in_client.post(
        SAVE_URL, {"work_key": "bad", "next": "/search/?q=dune"}, follow=True
    )

    assert "That isn&#x27;t a valid Open Library work key." in response.content.decode()


@pytest.mark.django_db
def test_an_offsite_next_url_is_ignored(logged_in_client, get_work_calls):
    response = logged_in_client.post(
        SAVE_URL, {"work_key": "OL893415W", "next": "https://evil.example.com/"}
    )

    assert response.status_code == 302
    assert response.url == "/search/"


@pytest.mark.django_db
def test_save_only_accepts_post(logged_in_client):
    assert logged_in_client.get(SAVE_URL).status_code == 405


@pytest.mark.django_db
def test_anonymous_users_cannot_save(client, get_work_calls):
    response = client.post(SAVE_URL, {"work_key": "OL893415W"})

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")
    assert not ShelfEntry.objects.exists()
