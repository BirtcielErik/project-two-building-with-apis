"""Tests for the Profile page: the display name and the share-link controls."""

import pytest

from accounts.models import new_share_token

# HTMX adds this header to every request it sends.
HTMX = {"HTTP_HX_REQUEST": "true"}


# --- Behavior 3: regenerating or disabling cuts off the old link ---------------


def test_regenerating_or_disabling_the_share_link_cuts_off_the_old_one(logged_in_client, reader):
    logged_in_client.post("/accounts/profile/share/create/", **HTMX)
    reader.refresh_from_db()
    first_url = f"/shared/{reader.share_token}/"
    assert reader.share_token
    assert logged_in_client.get(first_url).status_code == 200

    # Regenerate: the old link is "not found", and the new one works.
    logged_in_client.post("/accounts/profile/share/regenerate/", **HTMX)
    reader.refresh_from_db()
    second_url = f"/shared/{reader.share_token}/"
    assert second_url != first_url
    assert logged_in_client.get(first_url).status_code == 404
    assert logged_in_client.get(second_url).status_code == 200

    # Disable: sharing is off, and the last link is "not found" too.
    logged_in_client.post("/accounts/profile/share/disable/", **HTMX)
    reader.refresh_from_db()
    assert reader.share_token is None
    assert logged_in_client.get(second_url).status_code == 404


# --- The share card ----------------------------------------------------------------


def test_profile_shows_a_create_button_when_sharing_is_off(logged_in_client):
    page = logged_in_client.get("/accounts/profile/").content.decode()

    assert "Create share link" in page
    assert "never see your notes" in page
    assert "data-share-url" not in page


def test_profile_shows_the_full_link_with_copy_and_open_when_sharing_is_on(
    logged_in_client, reader
):
    reader.share_token = new_share_token()
    reader.save()

    page = logged_in_client.get("/accounts/profile/").content.decode()

    assert f'value="http://testserver/shared/{reader.share_token}/"' in page
    assert "data-copy-target" in page
    assert "Regenerate link" in page and "Disable sharing" in page
    # Regenerate and Disable each ask first.
    assert 'data-htmx-confirm="share-regenerate-dialog"' in page
    assert 'data-htmx-confirm="share-disable-dialog"' in page
    assert 'id="share-regenerate-dialog"' in page and 'id="share-disable-dialog"' in page


def test_creating_a_link_with_htmx_swaps_the_card_and_shows_a_toast(logged_in_client, reader):
    response = logged_in_client.post("/accounts/profile/share/create/", **HTMX)

    page = response.content.decode()
    reader.refresh_from_db()
    assert response.status_code == 200
    assert "<html" not in page
    assert 'id="share-card"' in page
    assert f"/shared/{reader.share_token}/" in page
    assert 'hx-swap-oob="true"' in page and "Share link created." in page


def test_disabling_with_htmx_returns_the_card_to_its_create_state(logged_in_client, reader):
    reader.share_token = new_share_token()
    reader.save()

    page = logged_in_client.post("/accounts/profile/share/disable/", **HTMX).content.decode()

    assert "Create share link" in page
    assert "Sharing is off. Your shelf is private again." in page


def test_share_actions_without_javascript_go_back_to_the_profile(logged_in_client, reader):
    response = logged_in_client.post("/accounts/profile/share/create/")

    assert response.status_code == 302
    assert response.url == "/accounts/profile/"
    reader.refresh_from_db()
    assert reader.share_token


@pytest.mark.parametrize("action", ["create", "regenerate", "disable"])
def test_share_actions_only_accept_post(logged_in_client, reader, action):
    reader.share_token = "unchanged-token"
    reader.save()

    response = logged_in_client.get(f"/accounts/profile/share/{action}/")

    assert response.status_code == 405
    reader.refresh_from_db()
    assert reader.share_token == "unchanged-token"


@pytest.mark.parametrize(
    "action", ["share/create", "share/regenerate", "share/disable", "display-name"]
)
def test_profile_actions_require_login(client, action):
    url = f"/accounts/profile/{action}/"

    response = client.post(url)

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


# --- Display name ----------------------------------------------------------------


def test_saving_a_display_name_with_htmx_updates_the_card_and_shows_a_toast(
    logged_in_client, reader
):
    response = logged_in_client.post(
        "/accounts/profile/display-name/", {"display_name": "  Maya  "}, **HTMX
    )

    page = response.content.decode()
    reader.refresh_from_db()
    assert reader.display_name == "Maya"  # Extra spaces are removed.
    assert 'id="display-name-card"' in page
    assert 'value="Maya"' in page
    assert "Display name saved." in page


def test_display_name_appears_on_the_shared_shelf(logged_in_client, reader, client):
    reader.share_token = new_share_token()
    reader.save()
    logged_in_client.post("/accounts/profile/display-name/", {"display_name": "Maya"}, **HTMX)

    page = logged_in_client.get(f"/shared/{reader.share_token}/").content.decode()

    assert "Maya</h1>" in page


def test_clearing_the_display_name_is_allowed(logged_in_client, reader):
    reader.display_name = "Maya"
    reader.save()

    response = logged_in_client.post(
        "/accounts/profile/display-name/", {"display_name": ""}, **HTMX
    )

    reader.refresh_from_db()
    assert reader.display_name == ""
    assert "Display name removed." in response.content.decode()


def test_too_long_display_name_shows_an_inline_error_and_is_not_saved(logged_in_client, reader):
    response = logged_in_client.post(
        "/accounts/profile/display-name/", {"display_name": "x" * 81}, **HTMX
    )

    page = response.content.decode()
    reader.refresh_from_db()
    assert response.status_code == 200  # HTMX only swaps 2xx responses.
    assert reader.display_name == ""
    assert "data-field-error" in page
    assert "at most 80 characters" in page
    assert "Display name saved." not in page


def test_display_name_without_javascript_redirects_with_a_message(logged_in_client, reader):
    response = logged_in_client.post(
        "/accounts/profile/display-name/", {"display_name": "Theo"}, follow=True
    )

    reader.refresh_from_db()
    assert reader.display_name == "Theo"
    assert response.redirect_chain == [("/accounts/profile/", 302)]
    assert "Display name saved." in response.content.decode()


def test_display_name_error_without_javascript_shows_the_full_profile(logged_in_client):
    response = logged_in_client.post("/accounts/profile/display-name/", {"display_name": "x" * 81})

    page = response.content.decode()
    assert response.status_code == 200
    assert "<html" in page
    assert "at most 80 characters" in page
