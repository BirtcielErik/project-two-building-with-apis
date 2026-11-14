"""Website URL routes for the shelf app."""

from django.urls import path

from shelf import views

app_name = "shelf"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("shelf/", views.my_shelf, name="my_shelf"),
    path("search/", views.search, name="search"),
]
