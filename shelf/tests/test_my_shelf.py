"""Tests for the My Shelf page and the logged-in navigation."""


def test_logged_in_user_visiting_home_goes_to_my_shelf(logged_in_client):
    response = logged_in_client.get("/")

    assert response.status_code == 302
    assert response.url == "/shelf/"


def test_empty_shelf_explains_itself_and_links_to_search(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert "data-empty-shelf" in html
    assert "Your shelf is empty" in html
    assert 'href="/search/"' in html


def test_navbar_shows_app_links_and_user_menu_when_logged_in(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert 'href="/search/"' in html
    assert 'href="/shelf/"' in html
    assert 'href="/accounts/profile/"' in html
    # Log out is a POST form, not a link.
    assert 'method="post" action="/accounts/logout/"' in html
    assert "reader" in html
    # The logged-out buttons are gone.
    assert 'href="/accounts/signup/"' not in html


def test_navbar_marks_the_current_page(logged_in_client):
    html = logged_in_client.get("/shelf/").content.decode()

    assert 'href="/shelf/" class="btn btn-neutral" aria-current="page"' in html
    assert 'href="/search/" class="btn btn-ghost"' in html


def test_navbar_shows_signup_and_login_when_logged_out(client):
    html = client.get("/").content.decode()

    assert 'href="/accounts/signup/"' in html
    assert 'href="/accounts/login/"' in html
    assert "/accounts/logout/" not in html
