"""DRF serializers: how shelf data is turned into JSON for the API."""

from rest_framework import serializers

from shelf import openlibrary
from shelf.models import Book, ShelfEntry


class BookSerializer(serializers.ModelSerializer):
    """Read-only book details nested inside a shelf entry.

    ``cover_url`` is worked out for the client, so API users don't need to
    know Open Library's cover URL scheme. It is ``null`` when there's no cover.
    """

    work_key = serializers.CharField(source="ol_work_key", read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["work_key", "title", "authors", "first_publish_year", "cover_url"]
        read_only_fields = fields

    def get_cover_url(self, book: Book) -> str | None:
        """Return the medium-size Open Library cover URL, or ``None`` with no cover ID."""
        return openlibrary.cover_url(book.cover_id, "M")


class ShelfEntrySerializer(serializers.ModelSerializer):
    """One book on the requesting user's shelf, with the user's reading details."""

    book = BookSerializer(read_only=True)

    class Meta:
        model = ShelfEntry
        fields = ["id", "book", "status", "rating", "finished_on", "added_at", "updated_at"]
        read_only_fields = ["id", "added_at", "updated_at"]
