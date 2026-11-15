"""Tests for the notes API (``/api/entries/<pk>/notes/``)."""

import pytest
from rest_framework.test import APIClient

from shelf.models import Note
from shelf.tests.helpers import add_to_shelf

# --- Behavior 2: notes on another user's entry are "not found" ------------------------


def test_note_requests_on_another_users_entry_are_404_and_change_nothing(
    token_client, reader, django_user_model
):
    mine = add_to_shelf(reader)
    my_note = Note.objects.create(entry=mine, text="Mine")
    other_user = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    theirs = add_to_shelf(other_user)
    their_note = Note.objects.create(entry=theirs, text="Their private thought")

    # My own entry's notes work, so the 404s below are about ownership, not routing.
    assert token_client.get(f"/api/entries/{mine.pk}/notes/").status_code == 200
    assert token_client.get(f"/api/entries/{mine.pk}/notes/{my_note.pk}/").status_code == 200

    theirs_url = f"/api/entries/{theirs.pk}/notes/"
    assert token_client.get(theirs_url).status_code == 404
    assert token_client.post(theirs_url, {"text": "Sneaky"}, format="json").status_code == 404
    assert token_client.get(f"{theirs_url}{their_note.pk}/").status_code == 404
    assert token_client.delete(f"{theirs_url}{their_note.pk}/").status_code == 404
    # Their note can't be reached through my entry's URL either.
    assert token_client.delete(f"/api/entries/{mine.pk}/notes/{their_note.pk}/").status_code == 404

    assert list(theirs.notes.values_list("text", flat=True)) == ["Their private thought"]


# --- Listing, adding, and deleting my own notes ----------------------------------------


def test_list_shows_only_this_entrys_notes_newest_first(token_client, reader):
    entry = add_to_shelf(reader)
    other_entry = add_to_shelf(reader, "OL893415W", "Dune", "Frank Herbert")
    older = Note.objects.create(entry=entry, text="Older")
    newer = Note.objects.create(entry=entry, text="Newer")
    Note.objects.create(entry=other_entry, text="About Dune")

    data = token_client.get(f"/api/entries/{entry.pk}/notes/").json()

    assert data["count"] == 2
    assert [note["id"] for note in data["results"]] == [newer.pk, older.pk]
    assert set(data["results"][0]) == {"id", "text", "created_at"}


def test_create_adds_a_note_to_the_entry_in_the_url(token_client, reader):
    entry = add_to_shelf(reader)

    response = token_client.post(
        f"/api/entries/{entry.pk}/notes/",
        {"text": "  Loved the riddles.  ", "entry": 999},  # "entry" in the body is ignored
        format="json",
    )

    assert response.status_code == 201
    note = Note.objects.get()
    assert (note.entry, note.text) == (entry, "Loved the riddles.")
    assert response.json()["id"] == note.pk
    assert response.json()["text"] == "Loved the riddles."


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   \n  "}])
def test_empty_or_whitespace_notes_are_400(token_client, reader, body):
    entry = add_to_shelf(reader)

    response = token_client.post(f"/api/entries/{entry.pk}/notes/", body, format="json")

    assert response.status_code == 400
    # The same message as the website's note form.
    assert response.json()["text"] == ["Write something before adding a note."]
    assert not Note.objects.exists()


def test_delete_removes_only_that_note(token_client, reader):
    entry = add_to_shelf(reader)
    keep = Note.objects.create(entry=entry, text="Keep")
    remove = Note.objects.create(entry=entry, text="Remove")

    response = token_client.delete(f"/api/entries/{entry.pk}/notes/{remove.pk}/")

    assert response.status_code == 204
    assert list(Note.objects.all()) == [keep]


@pytest.mark.parametrize("method", ["put", "patch"])
def test_notes_cannot_be_edited(token_client, reader, method):
    entry = add_to_shelf(reader)
    note = Note.objects.create(entry=entry, text="Original")

    response = getattr(token_client, method)(
        f"/api/entries/{entry.pk}/notes/{note.pk}/", {"text": "Edited"}, format="json"
    )

    assert response.status_code == 405
    note.refresh_from_db()
    assert note.text == "Original"


def test_a_missing_entry_is_404(token_client):
    assert token_client.get("/api/entries/999/notes/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [("get", "/api/entries/1/notes/"), ("post", "/api/entries/1/notes/")],
)
def test_notes_need_a_token_or_session(method, url):
    response = getattr(APIClient(), method)(url, {"text": "Hi"}, format="json")

    assert response.status_code == 401
