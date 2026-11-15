"""The REST API's views (DRF viewsets). Routes live in ``shelf/api_urls.py``."""

from django.db.models import QuerySet
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import APIException, ValidationError

from shelf import openlibrary, saving
from shelf.filters import ShelfEntryFilter
from shelf.models import ShelfEntry
from shelf.serializers import ShelfEntrySerializer


class OpenLibraryUnavailableError(APIException):
    """503: Open Library is down or slow right now, so the client should try again later."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Open Library is unavailable right now. Please try again later."
    default_code = "open_library_unavailable"


class OpenLibraryBadResponseError(APIException):
    """502: Open Library answered with something we couldn't read."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Open Library sent a response we couldn't read. Please try again later."
    default_code = "open_library_bad_response"


class ShelfEntryViewSet(viewsets.ModelViewSet):
    """The user's shelf entries: ``/api/entries/`` and ``/api/entries/<pk>/``.

    - GET lists entries (with the same ``q``, ``status``, ``min_rating``,
      ``rated``, ``ordering``, and ``page`` parameters as My Shelf) or shows one.
    - POST creates an entry from an Open Library work key.
    - PUT / PATCH change the status, rating, and finished date (never the book).
    - DELETE removes the entry together with its notes.
    """

    serializer_class = ShelfEntrySerializer
    filterset_class = ShelfEntryFilter

    def get_queryset(self) -> QuerySet[ShelfEntry]:
        """Return only the requesting user's entries.

        Because another user's entry is never in this queryset, asking for it
        gives "404 not found" (never "403 forbidden"), so nobody can discover
        which entry IDs exist on other people's shelves.
        """
        return self.request.user.shelf_entries.select_related("book")

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        """Save the new entry through the shared save flow and map its failures to responses.

        - A bad-format, unknown, or duplicate work key is a 400 on ``work_key``:
          the request itself is wrong.
        - Open Library being down is a 503, and an unreadable answer from it is
          a 502: "try again later" errors.
        """
        try:
            serializer.save()
        except saving.SaveError as error:
            raise ValidationError({"work_key": [str(error)]}) from None
        except openlibrary.OpenLibraryUnavailable:
            raise OpenLibraryUnavailableError() from None
        except openlibrary.OpenLibraryBadResponse:
            raise OpenLibraryBadResponseError() from None
