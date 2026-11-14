"""Tests for the public landing page."""

from django.contrib.staticfiles import finders


def test_landing_page_explains_the_app_and_offers_signup_and_login(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "One More Chapter" in html
    assert 'href="/accounts/signup/"' in html
    assert 'href="/accounts/login/"' in html
    assert html.count("data-feature-card") == 3


def test_htmx_is_served_from_our_static_files_not_a_cdn(client):
    html = client.get("/").content.decode()

    assert 'src="/static/js/htmx-2.0.7.min.js"' in html
    assert "unpkg.com" not in html
    assert "jsdelivr" not in html
    # The vendored file really exists where the static tag points.
    assert finders.find("js/htmx-2.0.7.min.js") is not None


def test_navbar_has_a_phone_menu(client):
    html = client.get("/").content.decode()

    # The collapsible menu button only appears below the "sm" breakpoint.
    assert 'aria-label="Open menu"' in html
    assert "sm:hidden" in html
