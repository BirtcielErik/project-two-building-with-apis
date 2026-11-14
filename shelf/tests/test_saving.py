"""Tests for saving a book to a shelf. ``openlibrary.get_work`` is replaced with fakes."""

import pytest

from shelf import openlibrary
from shelf.models import Book, ShelfEntry
from shelf.saving import AlreadyOnShelf, SaveError, save_to_shelf

HOBBIT = openlibrary.SearchResult(
    work_key="OL27482W",
    title="The Hobbit",
    authors=["J.R.R. Tolkien"],
    first_publish_year=1937,
    cover_id=14627509,
)


@pytest.fixture
def get_work_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Make ``openlibrary.get_work`` return The Hobbit; return the list of keys it was asked for."""
    calls: list[str] = []

    def fake_get_work(work_key: str) -> openlibrary.SearchResult:
        calls.append(work_key)
        return HOBBIT

    monkeypatch.setattr(openlibrary, "get_work", fake_get_work)
    return calls


@pytest.fixture
def reader(django_user_model):
    """A user who already has The Hobbit on their shelf."""
    user = django_user_model.objects.create_user(username="reader", password="pw-12345-long")
    book = Book.objects.create(ol_work_key="OL27482W", title="The Hobbit", authors="J.R.R. Tolkien")
    ShelfEntry.objects.create(user=user, book=book)
    return user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "work_key",
    [
        "",  # missing
        "hobbit",  # not a key at all
        "OL27482M",  # an edition or author key, not a work
        "/works/OL27482W",  # prefix not allowed
        "OL27482W title:x",  # query injection attempt
        "OL27482W",  # already on this user's shelf
    ],
)
def test_bad_keys_and_duplicates_are_rejected_before_calling_open_library(
    reader, get_work_calls: list[str], work_key: str
) -> None:
    with pytest.raises(SaveError):
        save_to_shelf(reader, work_key)

    assert get_work_calls == []  # no outbound request was made
    assert ShelfEntry.objects.filter(user=reader).count() == 1  # nothing new was saved


@pytest.mark.django_db
def test_a_book_already_in_the_database_can_be_saved_while_open_library_is_down(
    reader, django_user_model, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `reader` saved The Hobbit earlier, so its Book row already exists.
    def open_library_is_down(work_key: str) -> openlibrary.SearchResult:
        raise openlibrary.OpenLibraryUnavailable("Open Library did not respond.")

    monkeypatch.setattr(openlibrary, "get_work", open_library_is_down)
    friend = django_user_model.objects.create_user(username="friend", password="pw-12345-long")

    entry = save_to_shelf(friend, "OL27482W", status=ShelfEntry.Status.FINISHED)

    assert entry.user == friend
    assert entry.status == ShelfEntry.Status.FINISHED
    assert entry.book == Book.objects.get(ol_work_key="OL27482W")  # reused, not duplicated
    assert Book.objects.count() == 1


@pytest.mark.django_db
def test_saving_a_new_book_stores_a_snapshot_from_open_library(
    django_user_model, get_work_calls: list[str]
) -> None:
    user = django_user_model.objects.create_user(username="new", password="pw-12345-long")

    entry = save_to_shelf(user, "OL27482W")

    assert get_work_calls == ["OL27482W"]
    assert entry.status == ShelfEntry.Status.TO_BE_READ  # the default
    book = entry.book
    assert (book.ol_work_key, book.title, book.authors) == (
        "OL27482W",
        "The Hobbit",
        "J.R.R. Tolkien",
    )
    assert (book.first_publish_year, book.cover_id) == (1937, 14627509)


@pytest.mark.django_db
def test_an_unknown_key_is_a_save_error_and_stores_nothing(
    django_user_model, monkeypatch: pytest.MonkeyPatch
) -> None:
    def not_found(work_key: str) -> openlibrary.SearchResult:
        raise openlibrary.OpenLibraryNotFound(work_key)

    monkeypatch.setattr(openlibrary, "get_work", not_found)
    user = django_user_model.objects.create_user(username="new", password="pw-12345-long")

    with pytest.raises(SaveError, match="no book with that key"):
        save_to_shelf(user, "OL999999999W")

    assert not Book.objects.exists()
    assert not ShelfEntry.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "error", [openlibrary.OpenLibraryUnavailable(), openlibrary.OpenLibraryBadResponse()]
)
def test_open_library_failures_pass_through_for_new_books(
    django_user_model, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def failing(work_key: str) -> openlibrary.SearchResult:
        raise error

    monkeypatch.setattr(openlibrary, "get_work", failing)
    user = django_user_model.objects.create_user(username="new", password="pw-12345-long")

    with pytest.raises(type(error)):
        save_to_shelf(user, "OL27482W")

    assert not ShelfEntry.objects.exists()


@pytest.mark.django_db
def test_an_invalid_status_is_rejected(reader, get_work_calls: list[str]) -> None:
    with pytest.raises(SaveError, match="status"):
        save_to_shelf(reader, "OL1W", status="loved-it")

    assert get_work_calls == []


@pytest.mark.django_db
def test_a_duplicate_reports_the_existing_entry(reader) -> None:
    existing = ShelfEntry.objects.get(user=reader)

    with pytest.raises(AlreadyOnShelf) as raised:
        save_to_shelf(reader, "OL27482W")

    assert raised.value.entry == existing
