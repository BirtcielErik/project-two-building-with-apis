"""DRF serializers: how shelf data is turned into JSON for the API."""

from rest_framework import serializers

from shelf import openlibrary, saving
from shelf.models import Book, Note, ShelfEntry


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
    """One book on the requesting user's shelf, with the user's reading details.

    To create an entry the client sends only ``work_key`` (plus optional
    ``status``, ``rating``, and ``finished_on``). The server looks the book up
    itself, so nobody can fake the book details that every user shares. The
    entry always belongs to the requesting user; there is no ``user`` field.
    """

    book = BookSerializer(read_only=True)
    work_key = serializers.CharField(write_only=True)

    class Meta:
        model = ShelfEntry
        fields = [
            "id",
            "book",
            "work_key",
            "status",
            "rating",
            "finished_on",
            "added_at",
            "updated_at",
        ]
        read_only_fields = ["id", "added_at", "updated_at"]

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Build the serializer; ``work_key`` is required only when creating an entry."""
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["work_key"].required = False

    def validate_work_key(self, value: str) -> str:
        """Allow ``work_key`` only when creating an entry.

        An existing entry (and its notes) always stays about the same book, so
        sending ``work_key`` on an update is an error rather than being quietly
        ignored.
        """
        if self.instance is not None:
            raise serializers.ValidationError(
                "An entry's book can't be changed. Remove it and add the other book instead."
            )
        return value

    def create(self, validated_data: dict) -> ShelfEntry:
        """Save the book to the requesting user's shelf through the shared save flow."""
        user = self.context["request"].user
        return saving.save_to_shelf(
            user,
            validated_data["work_key"],
            status=validated_data.get("status", ShelfEntry.Status.TO_BE_READ),
            rating=validated_data.get("rating"),
            finished_on=validated_data.get("finished_on"),
        )


class SharedShelfEntrySerializer(serializers.ModelSerializer):
    """One book on a shared shelf, as anyone with the share link sees it.

    This is a separate serializer from ``ShelfEntrySerializer`` on purpose: it
    lists only what the owner agreed to share (book details, status, rating,
    finished date). Notes, the owner's username and ID, the entry's ID, and
    its timestamps are never included, even if fields are added elsewhere later.
    """

    book = BookSerializer(read_only=True)

    class Meta:
        model = ShelfEntry
        fields = ["book", "status", "rating", "finished_on"]
        read_only_fields = fields


class NoteSerializer(serializers.ModelSerializer):
    """One private note on a shelf entry: its text and when it was written.

    The entry comes from the URL (``/api/entries/<pk>/notes/``), not the body.
    """

    class Meta:
        model = Note
        fields = ["id", "text", "created_at"]
        read_only_fields = ["id", "created_at"]
        # Spaces at the start and end are trimmed, so a note of only whitespace
        # is blank and rejected, with the same message as the website.
        extra_kwargs = {
            "text": {
                "error_messages": {
                    "required": "Write something before adding a note.",
                    "blank": "Write something before adding a note.",
                }
            }
        }
