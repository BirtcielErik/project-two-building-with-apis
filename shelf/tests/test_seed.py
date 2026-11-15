"""Tests for the ``seed`` management command."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from shelf.management.commands.seed import DEMO_PASSWORD
from shelf.models import Book, Note, ShelfEntry
from shelf.tests.helpers import add_to_shelf

ALL_STATUSES = {choice.value for choice in ShelfEntry.Status}


def run_seed() -> str:
    """Run ``python manage.py seed`` and return what it printed."""
    out = StringIO()
    call_command("seed", stdout=out)
    return out.getvalue()


def snapshot(users) -> list[tuple]:
    """Describe each user's profile and whole shelf as plain values that can be compared."""
    return [
        (
            user.username,
            user.display_name,
            bool(user.share_token),
            sorted(
                (
                    entry.book.ol_work_key,
                    entry.status,
                    entry.rating,
                    entry.finished_on,
                    sorted(entry.notes.values_list("text", flat=True)),
                )
                for entry in user.shelf_entries.select_related("book")
            ),
        )
        for user in users.order_by("username")
    ]


# --- Behavior 3: seeding is repeatable and leaves other users alone ------------


@pytest.mark.django_db
def test_seed_is_repeatable_and_leaves_other_users_alone():
    user_model = get_user_model()
    bystander = user_model.objects.create_user(username="bystander", password="pw-12345-long")
    their_entry = add_to_shelf(bystander, rating=3)
    Note.objects.create(entry=their_entry, text="A bystander's note")
    before = snapshot(user_model.objects.filter(pk=bystander.pk))

    run_seed()
    demo_users = user_model.objects.exclude(pk=bystander.pk)
    first = snapshot(demo_users)
    entry_count, note_count = ShelfEntry.objects.count(), Note.objects.count()
    run_seed()

    # Running it again leaves exactly the same data: no duplicates, nothing lost.
    assert snapshot(demo_users) == first
    assert ShelfEntry.objects.count() == entry_count
    assert Note.objects.count() == note_count

    # Two demo users, each with a realistic shelf.
    assert demo_users.count() == 2
    for user in demo_users:
        entries = user.shelf_entries.all()
        assert 15 <= entries.count() <= 20
        assert {entry.status for entry in entries} == ALL_STATUSES
        assert entries.filter(rating__isnull=False).exists()
        assert entries.filter(rating__isnull=True).exists()
        assert entries.filter(finished_on__isnull=False).exists()
        assert Note.objects.filter(entry__user=user).exists()
    # One is ready for sharing, the other has sharing off.
    sharing = [user for user in demo_users if user.share_token]
    assert len(sharing) == 1
    assert sharing[0].display_name
    assert not demo_users.exclude(pk=sharing[0].pk).get().share_token

    # The bystander's shelf and notes are untouched.
    assert snapshot(user_model.objects.filter(pk=bystander.pk)) == before


# --- Other seed details ------------------------------------------------------------


@pytest.mark.django_db
def test_seed_prints_how_to_log_in_and_the_password_works(client):
    output = run_seed()

    for username in ("demo_maya", "demo_theo"):
        assert f"{username} / {DEMO_PASSWORD}" in output
    assert client.login(username="demo_maya", password=DEMO_PASSWORD)


@pytest.mark.django_db
def test_reseeding_keeps_the_share_link(django_user_model):
    run_seed()
    token = django_user_model.objects.get(username="demo_maya").share_token
    run_seed()

    assert django_user_model.objects.get(username="demo_maya").share_token == token


@pytest.mark.django_db
def test_seed_reuses_existing_books_without_changing_them():
    # Someone already saved The Hobbit, so its Book row is shared.
    Book.objects.create(ol_work_key="OL27482W", title="The Hobbit (as first saved)")

    run_seed()

    assert Book.objects.filter(ol_work_key="OL27482W").count() == 1
    assert Book.objects.get(ol_work_key="OL27482W").title == "The Hobbit (as first saved)"
