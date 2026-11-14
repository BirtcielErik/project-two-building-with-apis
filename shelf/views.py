"""Website views for the shelf app."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def landing(request: HttpRequest) -> HttpResponse:
    """Show the public landing page that explains what One More Chapter does."""
    return render(request, "shelf/landing.html")
