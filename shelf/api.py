"""The REST API's views (DRF viewsets). Routes live in ``shelf/api_urls.py``."""

from django.db.models import QuerySet
from rest_framework import viewsets

from shelf.filters import ShelfEntryFilter
from shelf.models import ShelfEntry
from shelf.serializers import ShelfEntrySerializer


class ShelfEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """List the user's shelf entries (``/api/entries/``) or show one (``/api/entries/<pk>/``).

    The list takes the same ``q``, ``status``, ``min_rating``, ``rated``,
    ``ordering``, and ``page`` parameters as the My Shelf page.
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
