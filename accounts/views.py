"""Website views for accounts: signup and the Profile page.

Login and logout use Django's built-in views (see ``accounts/urls.py``).
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from rest_framework.authtoken.models import Token

from accounts.forms import DisplayNameForm, SignupForm
from accounts.models import User, new_share_token
from shelf.htmx import is_htmx


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
    """Show the Profile page: display name, share link, and API access cards."""
    return _render_profile(request, DisplayNameForm(instance=request.user))


def _render_profile(request: HttpRequest, name_form: DisplayNameForm) -> HttpResponse:
    """Render the full Profile page with ``name_form`` (which may show errors)."""
    context = {"name_form": name_form, **_share_context(request), **_api_token_context(request)}
    return render(request, "accounts/profile.html", context)


# --- Display name ---------------------------------------------------------------


@login_required
@require_POST
def display_name_update(request: HttpRequest) -> HttpResponse:
    """Save the display name shown on the user's shared shelf.

    HTMX requests get the display name card back: with a toast when saved, or
    with the error under the field (nothing is saved). Without JavaScript, a
    save goes back to the Profile page, and an error shows the full page.
    """
    # Bind the form to a fresh copy of the user, so a rejected name never
    # changes request.user (which the navbar and the rest of the page use).
    user = User.objects.get(pk=request.user.pk)
    form = DisplayNameForm(request.POST, instance=user)
    saved = form.is_valid()
    if saved:
        form.save()
        if user.display_name:
            messages.success(
                request, f"Display name saved. Your shared shelf now says “{user.display_name}”."
            )
        else:
            messages.success(request, "Display name removed.")

    if not is_htmx(request):
        if not saved:
            return _render_profile(request, form)
        return redirect("accounts:profile")

    # After a save, show the cleaned value (extra spaces removed).
    name_form = DisplayNameForm(instance=user) if saved else form
    return render(
        request, "accounts/partials/display_name_card_response.html", {"name_form": name_form}
    )


# --- Share link -----------------------------------------------------------------


def _share_context(request: HttpRequest) -> dict[str, object]:
    """Return what the share card needs: the full share URL, or ``None`` when sharing is off."""
    token = request.user.share_token
    share_url = None
    if token:
        share_url = request.build_absolute_uri(reverse("shelf:shared_shelf", args=[token]))
    return {"share_url": share_url}


def _share_card_response(request: HttpRequest, message: str) -> HttpResponse:
    """Finish a share-link action: show ``message`` as a toast and the updated card.

    HTMX requests get just the share card (plus the toast). Without
    JavaScript, the browser goes back to the Profile page.
    """
    messages.success(request, message)
    if not is_htmx(request):
        return redirect("accounts:profile")
    return render(request, "accounts/partials/share_card_response.html", _share_context(request))


@login_required
@require_POST
def share_create(request: HttpRequest) -> HttpResponse:
    """Turn sharing on by giving the user a new share link."""
    _set_share_token(request, new_share_token())
    return _share_card_response(request, "Share link created.")


@login_required
@require_POST
def share_regenerate(request: HttpRequest) -> HttpResponse:
    """Replace the user's share link with a new one, so the old link stops working."""
    _set_share_token(request, new_share_token())
    return _share_card_response(request, "New share link created. The old link no longer works.")


@login_required
@require_POST
def share_disable(request: HttpRequest) -> HttpResponse:
    """Turn sharing off: remove the share link, so the shelf is private again."""
    _set_share_token(request, None)
    return _share_card_response(request, "Sharing is off. Your shelf is private again.")


def _set_share_token(request: HttpRequest, token: str | None) -> None:
    """Save ``token`` as the logged-in user's share token (``None`` turns sharing off).

    The shared page looks owners up by this token, so the moment it changes,
    any old link stops matching anyone and shows "not found".
    """
    request.user.share_token = token
    request.user.save(update_fields=["share_token"])


# --- API token ------------------------------------------------------------------

# How many characters at the end of the token stay visible while it's masked.
TOKEN_VISIBLE_CHARS = 4


def _api_token_context(request: HttpRequest) -> dict[str, object]:
    """Return what the API access card needs: the user's token and its masked form.

    A user gets their token the first time they open the Profile page.
    """
    token, _ = Token.objects.get_or_create(user=request.user)
    hidden = len(token.key) - TOKEN_VISIBLE_CHARS
    return {"api_token": token.key, "api_token_masked": "•" * hidden + token.key[hidden:]}


@login_required
@require_POST
def api_token_regenerate(request: HttpRequest) -> HttpResponse:
    """Give the user a new API token, so the old one stops working.

    HTMX requests get the API access card back (plus a toast). Without
    JavaScript, the browser goes back to the Profile page.
    """
    # Deleting the old token row means its key no longer matches anyone, so the
    # API rejects it at once (401). A fresh, random key replaces it.
    with transaction.atomic():
        Token.objects.filter(user=request.user).delete()
        Token.objects.create(user=request.user)
    messages.success(request, "New API token created. The old token no longer works.")
    if not is_htmx(request):
        return redirect("accounts:profile")
    return render(
        request, "accounts/partials/api_token_card_response.html", _api_token_context(request)
    )
