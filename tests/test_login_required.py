"""Tests that private pages are only shown to logged-in users."""

import pytest

PRIVATE_URLS = ["/shelf/", "/search/", "/accounts/profile/"]


@pytest.mark.django_db
@pytest.mark.parametrize("url", PRIVATE_URLS)
def test_anonymous_visitor_is_sent_to_login_and_brought_back_after(client, url):
    response = client.get(url)

    assert response.status_code == 302
    # "next" remembers where they were going, so login can send them back there.
    assert response.url == f"/accounts/login/?next={url}"


@pytest.mark.django_db
@pytest.mark.parametrize("url", PRIVATE_URLS)
def test_logged_in_user_can_open_private_pages(client, django_user_model, url):
    user = django_user_model.objects.create_user(username="reader", password="pw-12345-long")
    client.force_login(user)

    assert client.get(url).status_code == 200
