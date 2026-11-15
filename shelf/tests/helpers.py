"""Helpers shared by the shelf tests."""

from django.contrib.auth.models import AbstractBaseUser

from shelf.models import Book, ShelfEntry


def add_to_shelf(
    user: AbstractBaseUser,
    key: str = "OL27482W",
    title: str = "The Hobbit",
    authors: str = "J.R.R. Tolkien",
    *,
    first_publish_year: int | None = 1937,
    **fields: object,
) -> ShelfEntry:
    """Put a book on ``user``'s shelf and return the entry.

    The book is created if it's new, or reused if another test step already
    made it. ``fields`` are ShelfEntry fields such as ``status`` or ``rating``.
    """
    book, _ = Book.objects.get_or_create(
        ol_work_key=key,
        defaults={"title": title, "authors": authors, "first_publish_year": first_publish_year},
    )
    return ShelfEntry.objects.create(user=user, book=book, **fields)
