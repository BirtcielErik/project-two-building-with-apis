"""Top-level URL routes for One More Chapter.

Each app keeps its own routes in its ``urls.py``; this file just includes them.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("shelf.urls")),
]
