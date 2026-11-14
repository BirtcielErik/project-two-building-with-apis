"""Tests for logging in and out."""

import pytest

PASSWORD = "a-long-password-123"


@pytest.fixture
def reader(django_user_model):
    """A saved user with a known password."""
    return django_user_model.objects.create_user(username="reader", password=PASSWORD)


@pytest.mark.django_db
def test_login_page_shows_the_form_and_links_to_signup(client):
    html = client.get("/accounts/login/").content.decode()

    assert 'name="username"' in html
    assert 'name="password"' in html
    assert 'href="/accounts/signup/"' in html


def test_login_with_correct_details_goes_to_my_shelf(client, reader):
    response = client.post("/accounts/login/", {"username": "reader", "password": PASSWORD})

    assert response.status_code == 302
    assert response.url == "/shelf/"
    assert client.session["_auth_user_id"] == str(reader.pk)


def test_login_returns_to_the_page_that_asked_for_it(client, reader):
    response = client.post(
        "/accounts/login/?next=/search/",
        {"username": "reader", "password": PASSWORD, "next": "/search/"},
    )

    assert response.status_code == 302
    assert response.url == "/search/"


def test_login_with_a_wrong_password_shows_an_error(client, reader):
    response = client.post("/accounts/login/", {"username": "reader", "password": "wrong"})

    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_login_with_blank_fields_shows_inline_field_errors(client, db):
    response = client.post("/accounts/login/", {"username": "", "password": ""})

    html = response.content.decode()
    assert html.count("data-field-error") == 2
    assert "This field is required." in html


def test_logout_is_a_post_that_ends_the_session(client, reader):
    client.force_login(reader)

    response = client.post("/accounts/logout/")

    assert response.status_code == 302
    assert response.url == "/"
    assert "_auth_user_id" not in client.session


def test_logout_by_get_is_not_allowed(client, reader):
    client.force_login(reader)

    response = client.get("/accounts/logout/")

    assert response.status_code == 405
    assert client.session["_auth_user_id"] == str(reader.pk)  # still logged in
