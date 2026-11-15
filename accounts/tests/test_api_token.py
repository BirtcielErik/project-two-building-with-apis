"""Tests for the Profile page's API access card (the user's API token)."""

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

# HTMX adds this header to every request it sends.
HTMX = {"HTTP_HX_REQUEST": "true"}


def _api_status_with(token_key: str) -> int:
    """Call the API with ``token_key`` (and no login session) and return the status code."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
    return client.get("/api/entries/").status_code


# --- Behavior 3: regenerating the token turns off the old one ----------------------


def test_regenerating_the_api_token_turns_off_the_old_one(logged_in_client, reader):
    old_key = Token.objects.create(user=reader).key
    assert _api_status_with(old_key) == 200

    logged_in_client.post("/accounts/profile/api-token/regenerate/", **HTMX)

    new_key = Token.objects.get(user=reader).key
    assert new_key != old_key
    assert _api_status_with(old_key) == 401
    assert _api_status_with(new_key) == 200


# --- The API access card -------------------------------------------------------------


def test_profile_gives_the_user_one_token_and_keeps_it(logged_in_client, reader):
    logged_in_client.get("/accounts/profile/")
    first_key = Token.objects.get(user=reader).key

    logged_in_client.get("/accounts/profile/")

    assert Token.objects.filter(user=reader).count() == 1
    assert Token.objects.get(user=reader).key == first_key


def test_profile_shows_the_token_masked_except_its_last_characters(logged_in_client, reader):
    key = Token.objects.create(user=reader).key

    page = logged_in_client.get("/accounts/profile/").content.decode()

    masked = "•" * (len(key) - 4) + key[-4:]
    assert f'value="{masked}"' in page
    # The full key only sits in data-secret, for the Reveal and Copy buttons.
    assert f'data-secret="{key}"' in page
    assert f'value="{key}"' not in page
    assert 'data-reveal-target="api-token"' in page
    assert 'data-copy-target="api-token"' in page
    # Regenerate asks first.
    assert 'data-htmx-confirm="api-token-regenerate-dialog"' in page
    assert 'id="api-token-regenerate-dialog"' in page


def test_regenerating_with_htmx_swaps_the_card_and_shows_a_toast(logged_in_client, reader):
    old_key = Token.objects.create(user=reader).key

    response = logged_in_client.post("/accounts/profile/api-token/regenerate/", **HTMX)

    page = response.content.decode()
    new_key = Token.objects.get(user=reader).key
    assert response.status_code == 200
    assert "<html" not in page
    assert 'id="api-token-card"' in page
    assert f'data-secret="{new_key}"' in page and old_key not in page
    assert 'hx-swap-oob="true"' in page and "The old token no longer works." in page


def test_regenerating_without_javascript_goes_back_to_the_profile(logged_in_client, reader):
    Token.objects.create(user=reader)

    response = logged_in_client.post("/accounts/profile/api-token/regenerate/", follow=True)

    assert response.redirect_chain == [("/accounts/profile/", 302)]
    assert "The old token no longer works." in response.content.decode()


def test_regenerate_needs_a_post_and_a_login(client, logged_in_client):
    assert logged_in_client.get("/accounts/profile/api-token/regenerate/").status_code == 405

    client.logout()
    response = client.post("/accounts/profile/api-token/regenerate/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")
