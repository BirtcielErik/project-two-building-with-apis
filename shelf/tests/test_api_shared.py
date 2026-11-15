"""Tests for the public shared-shelf API (``/api/shared/<share_token>/``)."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import new_share_token
from shelf.models import Note, ShelfEntry
from shelf.tests.helpers import add_to_shelf

# --- Behavior 1: the shared API is public and never leaks private data -------------------


def test_shared_api_is_public_and_paginated_with_no_notes_or_user_identifiers(reader):
    reader.share_token = new_share_token()
    reader.display_name = "Bookworm"
    reader.save()
    for n in range(13):  # one more than a page
        entry = add_to_shelf(
            reader,
            f"OL{n + 1}W",
            f"Book {n + 1}",
            status=ShelfEntry.Status.FINISHED,
            rating=4,
            finished_on=datetime.date(2026, 1, 2),
        )
        Note.objects.create(entry=entry, text="SECRET-NOTE-TEXT")

    response = APIClient().get(f"/api/shared/{reader.share_token}/")  # not logged in

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 13
    assert len(data["results"]) == 12
    assert data["next"].endswith(f"/api/shared/{reader.share_token}/?page=2")
    for item in data["results"]:
        # Only what the owner chose to share: no notes, entry IDs, or timestamps.
        assert set(item) == {"book", "status", "rating", "finished_on"}
        assert set(item["book"]) == {
            "work_key",
            "title",
            "authors",
            "first_publish_year",
            "cover_url",
        }
    assert item == {
        "book": item["book"],
        "status": "finished",
        "rating": 4,
        "finished_on": "2026-01-02",
    }
    body = response.content.decode()
    assert "SECRET-NOTE-TEXT" not in body
    assert "reader" not in body  # the username
    assert '"user' not in body  # no user / user_id keys anywhere


# --- Read-only, and only while the link is live ------------------------------------------


@pytest.fixture
def sharing_reader(reader):
    """``reader`` with sharing turned on and one book on their shelf."""
    reader.share_token = new_share_token()
    reader.save()
    add_to_shelf(reader)
    return reader


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_writes_to_the_shared_endpoint_are_405_and_change_nothing(sharing_reader, method):
    url = f"/api/shared/{sharing_reader.share_token}/"

    response = getattr(APIClient(), method)(url, {"status": "dnf"}, format="json")

    assert response.status_code == 405
    assert ShelfEntry.objects.get().status == "tbr"


def test_writes_are_405_even_for_the_logged_in_owner(sharing_reader, token_client):
    url = f"/api/shared/{sharing_reader.share_token}/"

    assert token_client.delete(url).status_code == 405
    assert ShelfEntry.objects.exists()


@pytest.mark.django_db
def test_an_unknown_token_is_404():
    assert APIClient().get("/api/shared/not-a-real-token/").status_code == 404


def test_old_links_are_404_after_regenerate_or_disable(sharing_reader, logged_in_client):
    old_token = sharing_reader.share_token

    logged_in_client.post("/accounts/profile/share/regenerate/")
    sharing_reader.refresh_from_db()
    new_token = sharing_reader.share_token

    assert APIClient().get(f"/api/shared/{old_token}/").status_code == 404
    assert APIClient().get(f"/api/shared/{new_token}/").status_code == 200

    logged_in_client.post("/accounts/profile/share/disable/")

    assert APIClient().get(f"/api/shared/{new_token}/").status_code == 404


def test_an_empty_shared_shelf_is_an_empty_list(reader):
    reader.share_token = new_share_token()
    reader.save()

    data = APIClient().get(f"/api/shared/{reader.share_token}/").json()

    assert (data["count"], data["results"]) == (0, [])
