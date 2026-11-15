"""URL routes for the REST API, included under ``/api/`` in ``config/urls.py``.

A DRF router builds the usual routes for a viewset:
``entries/`` (list) and ``entries/<pk>/`` (one entry).
"""

from rest_framework.routers import DefaultRouter

from shelf.api import ShelfEntryViewSet

app_name = "api"

router = DefaultRouter()
router.register("entries", ShelfEntryViewSet, basename="entry")

urlpatterns = router.urls
