"""URL routes for the REST API, included under ``/api/`` in ``config/urls.py``.

A DRF router builds the usual routes for a viewset:
``entries/`` (list) and ``entries/<pk>/`` (one entry).

Notes live under their entry, which a plain router can't express, so their
routes are written out by hand. Each ``as_view()`` maps HTTP methods to
viewset actions; a method that isn't listed (PUT, PATCH) gets a 405.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from shelf.api import NoteViewSet, SharedShelfView, ShelfEntryViewSet

app_name = "api"

router = DefaultRouter()
router.register("entries", ShelfEntryViewSet, basename="entry")

note_list = NoteViewSet.as_view({"get": "list", "post": "create"})
note_detail = NoteViewSet.as_view({"get": "retrieve", "delete": "destroy"})

urlpatterns = [
    path("entries/<int:entry_pk>/notes/", note_list, name="note-list"),
    path("entries/<int:entry_pk>/notes/<int:pk>/", note_detail, name="note-detail"),
    path("shared/<str:share_token>/", SharedShelfView.as_view(), name="shared-shelf"),
    *router.urls,
]
