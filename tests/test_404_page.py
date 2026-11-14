"""Tests for the themed "page not found" page."""


def test_unknown_url_shows_themed_404_page(client, settings):
    settings.DEBUG = False  # Django only uses the custom 404 page when debug is off.

    response = client.get("/this-page-does-not-exist/")

    assert response.status_code == 404
    html = response.content.decode()
    assert "Page not found" in html
    assert "One More Chapter" in html  # our site layout, not Django's plain page
    assert "css/tailwind.css" in html  # styled with our Tailwind/DaisyUI theme
    assert 'href="/"' in html  # a way back home
