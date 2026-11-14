"""Website views for accounts: signup and the Profile page.

Login and logout use Django's built-in views (see ``accounts/urls.py``).
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from accounts.forms import SignupForm


def signup(request: HttpRequest) -> HttpResponse:
    """Show the signup form, and on a valid POST create the user and log them in.

    A new user is sent straight to My Shelf so they can start right away.
    If the form has errors, the page is shown again with the errors next to
    the fields that caused them. Users who are already logged in skip the form.
    """
    if request.user.is_authenticated:
        return redirect("shelf:my_shelf")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("shelf:my_shelf")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """Show the Profile page.

    For now it only shows who is logged in; the display name, share link,
    and API token cards are added in later phases.
    """
    return render(request, "accounts/profile.html")
