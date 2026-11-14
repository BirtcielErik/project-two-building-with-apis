"""Tests for signing up."""

import pytest

from accounts.models import User


@pytest.mark.django_db
def test_signup_creates_the_user_logs_them_in_and_goes_to_my_shelf(client):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "newreader",
            "password1": "a-long-password-123",
            "password2": "a-long-password-123",
        },
    )

    assert response.status_code == 302
    assert response.url == "/shelf/"
    user = User.objects.get(username="newreader")
    # The session now belongs to the new user, so the next page sees them as logged in.
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_signup_page_shows_the_form_and_links_to_login(client):
    html = client.get("/accounts/signup/").content.decode()

    assert 'name="username"' in html
    assert 'name="password1"' in html
    assert 'name="password2"' in html
    assert 'href="/accounts/login/"' in html


@pytest.mark.django_db
def test_signup_with_mismatched_passwords_shows_an_inline_error_and_creates_nobody(client):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "newreader",
            "password1": "a-long-password-123",
            "password2": "a-different-password-456",
        },
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "data-field-error" in html
    assert "The two password fields didn" in html  # Django's wording (with an apostrophe)
    assert "input-error" in html  # the bad field is highlighted
    assert not User.objects.filter(username="newreader").exists()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_signup_with_a_taken_username_shows_an_inline_error(client, django_user_model):
    django_user_model.objects.create_user(username="taken", password="a-long-password-123")

    response = client.post(
        "/accounts/signup/",
        {
            "username": "taken",
            "password1": "a-long-password-123",
            "password2": "a-long-password-123",
        },
    )

    assert response.status_code == 200
    assert "A user with that username already exists." in response.content.decode()
    assert User.objects.filter(username="taken").count() == 1


@pytest.mark.django_db
def test_logged_in_user_visiting_signup_goes_to_my_shelf(client, django_user_model):
    user = django_user_model.objects.create_user(username="reader", password="pw-12345-long")
    client.force_login(user)

    response = client.get("/accounts/signup/")

    assert response.status_code == 302
    assert response.url == "/shelf/"
