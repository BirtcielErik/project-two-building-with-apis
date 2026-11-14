"""Website URL routes for the shelf app."""

from django.urls import path

from shelf import views

app_name = "shelf"

urlpatterns = [
    path("", views.landing, name="landing"),
]
