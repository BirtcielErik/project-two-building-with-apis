"""Website URL routes for the shelf app."""

from django.urls import path

from shelf import views

app_name = "shelf"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("shelf/", views.my_shelf, name="my_shelf"),
    path("shelf/<int:pk>/", views.entry_detail, name="entry_detail"),
    path("shelf/<int:pk>/update/", views.entry_update, name="entry_update"),
    path("shelf/<int:pk>/remove/", views.entry_remove, name="entry_remove"),
    path("shelf/<int:pk>/notes/", views.note_add, name="note_add"),
    path("shelf/<int:pk>/notes/<int:note_pk>/delete/", views.note_delete, name="note_delete"),
    path("search/", views.search, name="search"),
    path("search/save/", views.save_book, name="save_book"),
    path("shared/<str:share_token>/", views.shared_shelf, name="shared_shelf"),
]
