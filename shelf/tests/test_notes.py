"""Tests for notes on the book detail page: adding, listing, and deleting them."""

import datetime

import pytest
from django.utils import timezone

from shelf.models import Note, ShelfEntry
from shelf.tests.helpers import add_to_shelf

# HTMX adds this header to every request it sends.
HTMX = {"HTTP_HX_REQUEST": "true"}


# --- Behavior 2: notes on another user's entry are 404 ------------------------


def test_notes_on_another_users_entry_are_not_found(logged_in_client, reader, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    their_entry = add_to_shelf(other)
    their_note = Note.objects.create(entry=their_entry, text="Their private thought")
    my_entry = add_to_shelf(reader, key="OL893415W", title="Dune")
    my_note = Note.objects.create(entry=my_entry, text="My first thought")
    post = logged_in_client.post

    # Adding a note to their entry.
    assert post(f"/shelf/{their_entry.pk}/notes/", {"text": "Sneaky"}, **HTMX).status_code == 404
    # Deleting their note through their entry's URL...
    their_delete = f"/shelf/{their_entry.pk}/notes/{their_note.pk}/delete/"
    assert post(their_delete, **HTMX).status_code == 404
    # ...or by pairing it with my own entry's URL.
    mixed_delete = f"/shelf/{my_entry.pk}/notes/{their_note.pk}/delete/"
    assert post(mixed_delete, **HTMX).status_code == 404
    # Their notes are untouched.
    assert list(their_entry.notes.values_list("text", flat=True)) == ["Their private thought"]

    # The same requests work on my own entry and note, so the 404s above
    # come from the ownership rule, not from missing pages.
    assert post(f"/shelf/{my_entry.pk}/notes/", {"text": "Mine"}, **HTMX).status_code == 200
    my_delete = f"/shelf/{my_entry.pk}/notes/{my_note.pk}/delete/"
    assert post(my_delete, **HTMX).status_code == 200
    assert list(my_entry.notes.values_list("text", flat=True)) == ["Mine"]


# --- Adding notes ---------------------------------------------------------------


def add_note(entry: ShelfEntry, text: str, minutes_ago: int) -> Note:
    """Create a note on ``entry`` that was written ``minutes_ago`` minutes ago."""
    note = Note.objects.create(entry=entry, text=text)
    written_at = timezone.now() - datetime.timedelta(minutes=minutes_ago)
    Note.objects.filter(pk=note.pk).update(created_at=written_at)
    return note


def test_adding_a_note_puts_it_at_the_top_with_its_timestamp(logged_in_client, reader):
    entry = add_to_shelf(reader)
    add_note(entry, "An older thought", minutes_ago=60)

    response = logged_in_client.post(
        f"/shelf/{entry.pk}/notes/", {"text": "  Gollum's riddles!  "}, **HTMX
    )

    assert response.status_code == 200
    html = response.content.decode()
    # The new note is saved without the extra spaces, and listed first.
    note = entry.notes.get(text="Gollum's riddles!")
    assert html.index("Gollum&#x27;s riddles!") < html.index("An older thought")
    written = timezone.localtime(note.created_at)
    assert f"{written:%b} {written.day}, {written:%Y}" in html
    assert "Notes <span" in html and "(2)" in html
    # A success toast, and the Remove dialog's count is refreshed out of band.
    assert "Note added." in html
    assert 'id="remove-warning" class="py-3 text-sm" hx-swap-oob="true"' in html
    assert "<strong>2 notes</strong>" in html


@pytest.mark.parametrize("text", ["", "   \n\t  "], ids=["empty", "whitespace"])
def test_an_empty_note_is_rejected_inline(logged_in_client, reader, text):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/notes/", {"text": text}, **HTMX)

    # HTMX only swaps 200 responses, so the error comes back as a 200.
    assert response.status_code == 200
    html = response.content.decode()
    assert "data-field-error" in html
    assert "Write something before adding a note." in html
    assert "textarea-error" in html
    assert "Note added." not in html
    assert not entry.notes.exists()


def test_adding_a_note_without_htmx_returns_to_the_notes(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/notes/", {"text": "Plain form"})

    assert response.status_code == 302
    assert response.url == f"/shelf/{entry.pk}/#notes"
    assert entry.notes.get().text == "Plain form"
    assert "Note added." in logged_in_client.get(response.url).content.decode()


def test_an_empty_note_without_htmx_shows_the_full_page_with_the_error(logged_in_client, reader):
    entry = add_to_shelf(reader)

    response = logged_in_client.post(f"/shelf/{entry.pk}/notes/", {"text": " "})

    assert response.status_code == 200
    html = response.content.decode()
    assert "<h1" in html  # the whole page, not just the notes
    assert "Write something before adding a note." in html
    assert not entry.notes.exists()


# --- Listing notes ----------------------------------------------------------------


def test_detail_page_lists_notes_newest_first(logged_in_client, reader):
    entry = add_to_shelf(reader)
    add_note(entry, "First thought", minutes_ago=90)
    add_note(entry, "Latest thought", minutes_ago=5)
    add_note(entry, "Middle thought", minutes_ago=30)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert html.index("Latest thought") < html.index("Middle thought") < html.index("First thought")
    assert html.count("data-note>") == 3
    assert "data-notes-empty" not in html


def test_detail_page_shows_an_empty_state_without_notes(logged_in_client, reader):
    entry = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert "data-notes-empty" in html
    assert "No notes yet." in html
    assert f'action="/shelf/{entry.pk}/notes/"' in html


def test_add_note_form_leaves_validation_to_the_server(logged_in_client, reader):
    entry = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    # Without novalidate, the browser's own popup would block an empty note
    # before our styled "Write something…" error could show.
    form_tag = html[html.index(f'action="/shelf/{entry.pk}/notes/"') :].split(">", 1)[0]
    assert "novalidate" in form_tag


# --- Deleting notes ---------------------------------------------------------------


def test_deleting_a_note_removes_it_in_place(logged_in_client, reader):
    entry = add_to_shelf(reader)
    keep = add_note(entry, "Keep me", minutes_ago=10)
    gone = add_note(entry, "Delete me", minutes_ago=5)

    response = logged_in_client.post(f"/shelf/{entry.pk}/notes/{gone.pk}/delete/", **HTMX)

    assert response.status_code == 200
    html = response.content.decode()
    assert "Delete me" not in html
    assert "Keep me" in html
    assert "Note deleted." in html
    assert "<strong>1 note</strong>" in html
    assert list(entry.notes.all()) == [keep]


def test_deleting_the_last_note_shows_the_empty_state(logged_in_client, reader):
    entry = add_to_shelf(reader)
    note = add_note(entry, "Only one", minutes_ago=5)

    html = logged_in_client.post(
        f"/shelf/{entry.pk}/notes/{note.pk}/delete/", **HTMX
    ).content.decode()

    assert "data-notes-empty" in html
    assert "It has no notes." in html


def test_delete_buttons_ask_for_confirmation(logged_in_client, reader):
    entry = add_to_shelf(reader)
    add_note(entry, "A note", minutes_ago=5)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert 'data-htmx-confirm="note-delete-dialog"' in html
    assert '<dialog id="note-delete-dialog"' in html


def test_deleting_without_htmx_returns_to_the_notes(logged_in_client, reader):
    entry = add_to_shelf(reader)
    note = add_note(entry, "Bye", minutes_ago=5)

    response = logged_in_client.post(f"/shelf/{entry.pk}/notes/{note.pk}/delete/")

    assert response.status_code == 302
    assert response.url == f"/shelf/{entry.pk}/#notes"
    assert not entry.notes.exists()


@pytest.mark.parametrize("path", ["notes/", "notes/{note}/delete/"], ids=["add", "delete"])
def test_note_changes_must_be_posted(logged_in_client, reader, path):
    entry = add_to_shelf(reader)
    note = add_note(entry, "Still here", minutes_ago=5)

    response = logged_in_client.get(f"/shelf/{entry.pk}/" + path.format(note=note.pk))

    assert response.status_code == 405
    assert entry.notes.count() == 1


@pytest.mark.django_db
def test_anonymous_visitor_cannot_add_notes(client, django_user_model):
    owner = django_user_model.objects.create_user(username="owner", password="pw-12345-long")
    entry = add_to_shelf(owner)

    response = client.post(f"/shelf/{entry.pk}/notes/", {"text": "Hi"})

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")
    assert not entry.notes.exists()


# --- Notes and the rest of the shelf -----------------------------------------------


def test_removing_a_book_deletes_its_notes(logged_in_client, reader):
    entry = add_to_shelf(reader)
    add_note(entry, "One", minutes_ago=10)
    add_note(entry, "Two", minutes_ago=5)

    logged_in_client.post(f"/shelf/{entry.pk}/remove/")

    assert not Note.objects.exists()


def test_remove_dialog_says_how_many_notes_will_be_deleted(logged_in_client, reader):
    entry = add_to_shelf(reader)
    add_note(entry, "One", minutes_ago=10)
    add_note(entry, "Two", minutes_ago=5)

    html = logged_in_client.get(f"/shelf/{entry.pk}/").content.decode()

    assert "<strong>2 notes</strong>" in html


def test_shelf_rows_show_each_books_notes_count(logged_in_client, reader):
    hobbit = add_to_shelf(reader)
    dune = add_to_shelf(reader, key="OL893414W", title="Dune")
    add_to_shelf(reader, key="OL66554W", title="Pride and Prejudice")
    for minutes in (1, 2, 3):
        add_note(hobbit, f"Hobbit note {minutes}", minutes_ago=minutes)
    add_note(dune, "Spice!", minutes_ago=1)

    html = logged_in_client.get("/shelf/").content.decode()

    assert "📝 3 notes" in html
    assert "📝 1 note<" in html
    assert "📝 0 notes" in html
    # Notes don't inflate the sidebar's status counts: 3 books, not one per note.
    assert 'data-status-count="all">3<' in html
    assert 'data-status-count="tbr">3<' in html


def test_another_users_notes_never_appear_on_my_detail_page(
    logged_in_client, reader, django_user_model
):
    other = django_user_model.objects.create_user(username="other", password="pw-12345-long")
    add_note(add_to_shelf(other), "Their secret", minutes_ago=5)
    # Same book, so both entries point to the same shared Book row.
    mine = add_to_shelf(reader)

    html = logged_in_client.get(f"/shelf/{mine.pk}/").content.decode()

    assert "Their secret" not in html
    assert "data-notes-empty" in html
