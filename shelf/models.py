"""Database models for books and shelf entries. Notes arrive in a later phase."""

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def validate_not_in_future(value: datetime.date) -> None:
    """Reject a date that is later than today (in the site's time zone)."""
    if value > timezone.localdate():
        raise ValidationError("The finished date can't be in the future.")


class Book(models.Model):
    """One Open Library *work*, shared by every user who saves it.

    This is a snapshot of the book's display details, taken when it was first
    saved, so the shelf keeps working when Open Library is down. Users never
    edit these rows, and they are kept even when no shelf uses them, so they
    also act as a local cache of books we've already looked up.
    """

    ol_work_key = models.CharField(
        max_length=20,
        unique=True,
        help_text='Open Library work key without the "/works/" prefix, e.g. OL27482W.',
    )
    title = models.CharField(max_length=500)
    # Stored as one string ("Frank Herbert, Brian Herbert") so searching and
    # sorting by author are simple text operations.
    authors = models.CharField(max_length=500, blank=True, default="")
    first_publish_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cover_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        """Return the title, which is how books are shown in the admin."""
        return self.title

    @property
    def authors_display(self) -> str:
        """Return the authors as one comma-separated string (same as ``SearchResult``)."""
        return self.authors


class ShelfEntry(models.Model):
    """One book on one user's shelf, with that user's reading details."""

    class Status(models.TextChoices):
        """Where the user is with this book."""

        TO_BE_READ = "tbr", "To Be Read"
        READING = "reading", "Currently Reading"
        FINISHED = "finished", "Finished"
        DID_NOT_FINISH = "dnf", "Did Not Finish"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shelf_entries"
    )
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="shelf_entries")
    status = models.CharField(max_length=10, choices=Status, default=Status.TO_BE_READ)
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Optional 1–5 star rating, allowed at any status.",
    )
    finished_on = models.DateField(
        null=True,
        blank=True,
        validators=[validate_not_in_future],
        help_text="Optional date the user finished (or stopped) reading.",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "shelf entries"
        ordering = ["-added_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_book_per_user"),
        ]

    def __str__(self) -> str:
        """Return "<username>: <title>" for the admin."""
        return f"{self.user}: {self.book}"
