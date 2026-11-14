"""Website views for the shelf app."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def landing(request: HttpRequest) -> HttpResponse:
    """Show the public landing page that explains what One More Chapter does.

    Logged-in users don't need the sales pitch, so they go straight to My Shelf.
    """
    if request.user.is_authenticated:
        return redirect("shelf:my_shelf")
    return render(request, "shelf/landing.html")


@login_required
def my_shelf(request: HttpRequest) -> HttpResponse:
    """Show the user's bookshelf.

    Books can't be saved yet (that arrives with search), so for now the
    shelf always shows its empty state with a button to the Search page.
    """
    return render(request, "shelf/my_shelf.html")


@login_required
def search(request: HttpRequest) -> HttpResponse:
    """Show the Open Library search page. Searching itself is added in the next phase."""
    return render(request, "shelf/search.html")
