"""Tests for the API's rate limits (429 Too Many Requests).

The limits come from ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``: 60 a minute
per user, and 10 a minute for creating entries and for the shared shelf. The
``clear_cache`` fixture (``conftest.py``) resets the counters between tests.
"""

from rest_framework.test import APIClient

from accounts.models import new_share_token
from shelf.tests.helpers import add_to_shelf


def _assert_throttled(response) -> None:
    """Check ``response`` is a 429 that tells the client how long to wait."""
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
    assert "detail" in response.json()


def test_creating_entries_is_limited_to_10_a_minute(token_client):
    # Bad-format keys are rejected without calling Open Library, but still count.
    for _ in range(10):
        response = token_client.post("/api/entries/", {"work_key": "bad"}, format="json")
        assert response.status_code == 400

    _assert_throttled(token_client.post("/api/entries/", {"work_key": "bad"}, format="json"))
    # Reading isn't part of the stricter create limit.
    assert token_client.get("/api/entries/").status_code == 200


def test_the_shared_endpoint_is_limited_to_10_a_minute(reader):
    reader.share_token = new_share_token()
    reader.save()
    add_to_shelf(reader)
    url = f"/api/shared/{reader.share_token}/"
    visitor = APIClient()

    for _ in range(10):
        assert visitor.get(url).status_code == 200

    _assert_throttled(visitor.get(url))


def test_other_requests_are_limited_to_60_a_minute_per_user(token_client, reader):
    entry = add_to_shelf(reader)

    for _ in range(60):
        assert token_client.get(f"/api/entries/{entry.pk}/").status_code == 200

    _assert_throttled(token_client.get(f"/api/entries/{entry.pk}/notes/"))


def test_counters_start_fresh_in_each_test_part_1(token_client):
    """With ``part_2`` below, shows the cache fixture resets the counters between tests."""
    for _ in range(10):
        token_client.post("/api/entries/", {"work_key": "bad"}, format="json")

    _assert_throttled(token_client.post("/api/entries/", {"work_key": "bad"}, format="json"))


def test_counters_start_fresh_in_each_test_part_2(token_client):
    """Runs after ``part_1`` used up the limit; it would be a 429 if counters leaked."""
    response = token_client.post("/api/entries/", {"work_key": "bad"}, format="json")

    assert response.status_code == 400
