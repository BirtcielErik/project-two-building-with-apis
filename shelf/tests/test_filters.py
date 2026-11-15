"""Tests for the shelf FilterSet (shared by My Shelf and the API)."""

import datetime

import pytest

from shelf.filters import ShelfEntryFilter
from shelf.models import ShelfEntry
from shelf.tests.helpers import add_to_shelf


def filtered_titles(user, **params: str) -> list[str]:
    """Run the FilterSet over ``user``'s shelf with URL ``params``; return the titles in order."""
    filterset = ShelfEntryFilter(params, queryset=user.shelf_entries.select_related("book"))
    return [entry.book.title for entry in filterset.qs]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        ("rating", ["Low", "High", "Empty"]),
        ("-rating", ["High", "Low", "Empty"]),
        ("finished", ["Low", "High", "Empty"]),
        ("-finished", ["High", "Low", "Empty"]),
    ],
)
def test_books_without_a_value_sort_last_in_both_directions(reader, ordering, expected):
    add_to_shelf(reader, "OL1W", "Empty")  # no rating, no finished date
    add_to_shelf(reader, "OL2W", "Low", rating=2, finished_on=datetime.date(2026, 1, 5))
    add_to_shelf(reader, "OL3W", "High", rating=5, finished_on=datetime.date(2026, 6, 20))

    assert filtered_titles(reader, ordering=ordering) == expected


# --- Each filter on its own ----------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["dune", "DUNE", "herbert", "  Herbert  "])
def test_search_matches_title_or_author_ignoring_case(reader, query):
    add_to_shelf(reader, "OL1W", "Dune", "Frank Herbert")
    add_to_shelf(reader, "OL2W", "Emma", "Jane Austen")

    assert filtered_titles(reader, q=query) == ["Dune"]


@pytest.mark.django_db
def test_search_matches_part_of_a_word(reader):
    add_to_shelf(reader, "OL1W", "The Fellowship of the Ring", "J.R.R. Tolkien")

    assert filtered_titles(reader, q="fellow") == ["The Fellowship of the Ring"]


@pytest.mark.django_db
def test_status_filter(reader):
    add_to_shelf(reader, "OL1W", "Reading Now", status=ShelfEntry.Status.READING)
    add_to_shelf(reader, "OL2W", "Gave Up", status=ShelfEntry.Status.DID_NOT_FINISH)

    assert filtered_titles(reader, status="dnf") == ["Gave Up"]
    assert filtered_titles(reader, status="reading") == ["Reading Now"]


@pytest.mark.django_db
def test_min_rating_keeps_that_rating_and_above_and_skips_unrated(reader):
    add_to_shelf(reader, "OL1W", "Three", rating=3)
    add_to_shelf(reader, "OL2W", "Four", rating=4)
    add_to_shelf(reader, "OL3W", "Five", rating=5)
    add_to_shelf(reader, "OL4W", "Unrated")

    assert filtered_titles(reader, min_rating="4", ordering="rating") == ["Four", "Five"]


@pytest.mark.django_db
def test_rated_filter(reader):
    add_to_shelf(reader, "OL1W", "Rated", rating=2)
    add_to_shelf(reader, "OL2W", "Unrated")

    assert filtered_titles(reader, rated="yes") == ["Rated"]
    assert filtered_titles(reader, rated="no") == ["Unrated"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "params",
    [
        {"status": "lost"},
        {"min_rating": "9"},
        {"min_rating": "0"},
        {"min_rating": "lots"},
        {"rated": "maybe"},
    ],
)
def test_invalid_filter_values_are_reported(reader, params):
    """The website ignores these; the API (later) turns them into a 400."""
    filterset = ShelfEntryFilter(params, queryset=reader.shelf_entries.all())

    assert not filterset.is_valid()
    assert set(filterset.errors) == set(params)


@pytest.mark.django_db
def test_no_parameters_lists_the_whole_shelf_newest_first(reader):
    add_to_shelf(reader, "OL1W", "Older")
    add_to_shelf(reader, "OL2W", "Newer")

    assert filtered_titles(reader) == ["Newer", "Older"]


# --- Sorting -------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        ("title", ["Alpha", "Bravo", "Charlie"]),
        ("-title", ["Charlie", "Bravo", "Alpha"]),
        ("author", ["Charlie", "Alpha", "Bravo"]),  # Adams, Brown, Clark
        ("-author", ["Bravo", "Alpha", "Charlie"]),
        ("rating", ["Bravo", "Charlie", "Alpha"]),  # 1, 3, 5
        ("-rating", ["Alpha", "Charlie", "Bravo"]),
        ("added", ["Bravo", "Alpha", "Charlie"]),  # saved in that order
        ("-added", ["Charlie", "Alpha", "Bravo"]),
        ("finished", ["Charlie", "Bravo", "Alpha"]),  # Jan, Feb, Mar
        ("-finished", ["Alpha", "Bravo", "Charlie"]),
        ("updated", ["Charlie", "Bravo", "Alpha"]),  # Charlie never edited; Alpha edited last
        ("-updated", ["Alpha", "Bravo", "Charlie"]),
    ],
)
def test_every_sort_option_works_in_both_directions(reader, ordering, expected):
    bravo = add_to_shelf(
        reader, "OL2W", "Bravo", "Clark", rating=1, finished_on=datetime.date(2026, 2, 1)
    )
    alpha = add_to_shelf(
        reader, "OL1W", "Alpha", "Brown", rating=5, finished_on=datetime.date(2026, 3, 1)
    )
    add_to_shelf(
        reader, "OL3W", "Charlie", "Adams", rating=3, finished_on=datetime.date(2026, 1, 1)
    )
    # Editing an entry moves its updated_at forward (added_at stays put).
    bravo.save()
    alpha.save()

    assert filtered_titles(reader, ordering=ordering) == expected


@pytest.mark.django_db
def test_ties_are_broken_by_newest_addition(reader):
    add_to_shelf(reader, "OL1W", "First", rating=4)
    add_to_shelf(reader, "OL2W", "Second", rating=4)

    assert filtered_titles(reader, ordering="rating") == ["Second", "First"]
    assert filtered_titles(reader, ordering="-rating") == ["Second", "First"]


@pytest.mark.django_db
def test_unknown_sort_falls_back_to_newest_first(reader):
    add_to_shelf(reader, "OL1W", "Older")
    add_to_shelf(reader, "OL2W", "Newer")

    assert filtered_titles(reader, ordering="price") == ["Newer", "Older"]
