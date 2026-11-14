"""Saving an Open Library book to a user's shelf.

The website (Search page) and the API both save books through
``save_to_shelf``, so the rules are identical everywhere.
"""

import re

from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction

from shelf import openlibrary
from shelf.models import Book, ShelfEntry

# "OL", one or more digits, "W": the shape of every Open Library work key.
WORK_KEY_PATTERN = re.compile(r"OL\d+W")


class SaveError(Exception):
    """The book can't be saved. ``str(error)`` is a message to show the user.

    Open Library outages are *not* ``SaveError``s: ``OpenLibraryUnavailable``
    and ``OpenLibraryBadResponse`` pass through so callers can tell "try again
    later" apart from "this request is wrong".
    """


class AlreadyOnShelf(SaveError):
    """The book is already on this user's shelf. ``entry`` is that existing entry."""

    def __init__(self, entry: ShelfEntry) -> None:
        """Remember the existing entry so callers can link to it."""
        super().__init__("This book is already on your shelf.")
        self.entry = entry


def is_valid_work_key(work_key: str) -> bool:
    """Return whether ``work_key`` is exactly an Open Library work key, like ``"OL27482W"``.

    Checking this before any request blocks query injection (the key goes into
    a search query) and saves requests that could never succeed.
    """
    return WORK_KEY_PATTERN.fullmatch(work_key) is not None


def save_to_shelf(
    user: AbstractBaseUser, work_key: str, status: str = ShelfEntry.Status.TO_BE_READ
) -> ShelfEntry:
    """Save the work ``work_key`` to ``user``'s shelf with ``status`` and return the new entry.

    Cheap checks run first, so a bad request never costs a call to Open Library:

    1. the key must look like ``OL<digits>W``;
    2. the book must not already be on this user's shelf.

    Then the ``Book`` row is reused if any user saved this book before, and
    only a brand-new book is looked up on Open Library. That's why saving a
    known book still works while Open Library is down.

    Raises ``SaveError`` (or its subclass ``AlreadyOnShelf``) when the request
    can't succeed, and lets ``OpenLibraryUnavailable`` / ``OpenLibraryBadResponse``
    through when the lookup fails.
    """
    if status not in ShelfEntry.Status.values:
        raise SaveError("Choose a valid reading status.")
    if not is_valid_work_key(work_key):
        raise SaveError("That isn't a valid Open Library work key.")
    existing = ShelfEntry.objects.filter(user=user, book__ol_work_key=work_key).first()
    if existing is not None:
        raise AlreadyOnShelf(existing)

    book = Book.objects.filter(ol_work_key=work_key).first()
    if book is None:
        book = _create_book_from_open_library(work_key)
    try:
        # A savepoint, so a failed insert doesn't break the surrounding transaction.
        with transaction.atomic():
            return ShelfEntry.objects.create(user=user, book=book, status=status)
    except IntegrityError:
        # A double-click raced past the duplicate check above.
        raise AlreadyOnShelf(ShelfEntry.objects.get(user=user, book=book)) from None


def _create_book_from_open_library(work_key: str) -> Book:
    """Look up ``work_key`` on Open Library and store a snapshot of its details as a ``Book``.

    Raises ``SaveError`` when Open Library has no such work.
    """
    try:
        result = openlibrary.get_work(work_key)
    except openlibrary.OpenLibraryNotFound:
        raise SaveError("Open Library has no book with that key.") from None
    # get_or_create: if another request stored this book a moment ago, reuse it.
    book, _created = Book.objects.get_or_create(
        ol_work_key=result.work_key,
        defaults={
            "title": result.title,
            "authors": result.authors_display,
            "first_publish_year": result.first_publish_year,
            "cover_id": result.cover_id,
        },
    )
    return book
