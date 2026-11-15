"""The REST API's views (DRF viewsets). Routes live in ``shelf/api_urls.py``."""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, permissions, serializers, status, viewsets
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.request import Request
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle

from shelf import openlibrary, saving
from shelf.filters import TIEBREAK_ORDERING, ShelfEntryFilter
from shelf.models import Note, ShelfEntry
from shelf.serializers import NoteSerializer, SharedShelfEntrySerializer, ShelfEntrySerializer


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

    def get_throttles(self) -> list[BaseThrottle]:
        """Return the rate limits for this request.

        Every request counts toward the user's general limit. Creating an entry
        also counts toward the stricter ``entry_create`` limit, because a new
        book means a request to Open Library.
        """
        throttles = super().get_throttles()
        if self.action == "create":
            self.throttle_scope = "entry_create"
            throttles.append(ScopedRateThrottle())
        return throttles

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


class NoteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Notes on one shelf entry: ``/api/entries/<entry_pk>/notes/[<pk>/]``.

    Notes can be listed, added, viewed, and deleted, but never edited, so there
    is no update mixin and PUT / PATCH get "405 Method Not Allowed".
    """

    serializer_class = NoteSerializer

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        """Before any action runs, find the entry in the URL among the caller's own entries.

        DRF calls ``initial()`` after checking authentication, so this runs only
        for logged-in callers. An entry that isn't theirs is "404 not found"
        for every action, including adding a note, and it's checked before the
        note's text, so a bad body can't reveal that the entry exists.
        """
        super().initial(request, *args, **kwargs)
        self.entry = get_object_or_404(request.user.shelf_entries, pk=kwargs["entry_pk"])

    def get_queryset(self) -> QuerySet[Note]:
        """Return the notes on the caller's entry, newest first.

        A note that belongs to another entry isn't in here, so asking for it is a 404.
        """
        return self.entry.notes.all()

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        """Attach the new note to the caller's entry from the URL."""
        serializer.save(entry=self.entry)


class SharedShelfView(generics.ListAPIView):
    """A shared shelf, read-only, for anyone with its link: ``/api/shared/<share_token>/``.

    No login is needed. A token that doesn't match any user (wrong,
    regenerated, or disabled) is "404 not found". The list is paginated
    like the owner's API, newest additions first.

    It is read-only: ``ListAPIView`` only handles GET (and HEAD / OPTIONS),
    so POST, PUT, PATCH, and DELETE get "405 Method Not Allowed".

    Visitors aren't logged in, so the stricter ``shared`` limit counts
    requests per IP address.
    """

    serializer_class = SharedShelfEntrySerializer
    permission_classes = [permissions.AllowAny]
    # Nobody logs in here, so skip reading the Authorization header or session.
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "shared"

    def get_queryset(self) -> QuerySet[ShelfEntry]:
        """Return the shelf owner's entries, or raise a 404 for an unknown token."""
        owner = get_object_or_404(get_user_model(), share_token=self.kwargs["share_token"])
        return owner.shelf_entries.select_related("book").order_by(*TIEBREAK_ORDERING)
