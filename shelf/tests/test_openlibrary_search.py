"""Tests for the Open Library search function, faked at the HTTP level with ``responses``."""

import pytest
import requests
import responses

from shelf import openlibrary

DUNE_RESPONSE = {
    "numFound": 1,
    "docs": [
        {
            "key": "/works/OL893415W",
            "title": "Dune",
            "author_name": ["Frank Herbert"],
            "first_publish_year": 1965,
            "cover_i": 11481354,
        }
    ],
}


@responses.activate
def test_search_parses_results_into_books() -> None:
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    page = openlibrary.search("dune")

    assert page.total == 1
    assert page.page == 1
    assert page.results == [
        openlibrary.SearchResult(
            work_key="OL893415W",  # the "/works/" prefix is removed
            title="Dune",
            authors=["Frank Herbert"],
            first_publish_year=1965,
            cover_id=11481354,
        )
    ]


@responses.activate
def test_search_sends_restricted_fields_page_size_and_timeout() -> None:
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    openlibrary.search("  the   hobbit ", page=3)

    request = responses.calls[0].request
    assert request.params == {
        "q": "the hobbit",  # trimmed, with inner spaces collapsed
        "fields": "key,title,author_name,first_publish_year,cover_i",
        "limit": "20",
        "page": "3",
    }
    assert request.req_kwargs["timeout"] == 5


@responses.activate
def test_user_agent_includes_contact_email_when_configured(settings) -> None:
    settings.OPENLIBRARY_CONTACT_EMAIL = "reader@example.com"
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    openlibrary.search("dune")

    assert responses.calls[0].request.headers["User-Agent"] == (
        "OneMoreChapter/0.1.0 (reader@example.com)"
    )


@responses.activate
def test_user_agent_still_identifies_the_app_without_an_email(settings) -> None:
    settings.OPENLIBRARY_CONTACT_EMAIL = ""
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    openlibrary.search("dune")

    assert responses.calls[0].request.headers["User-Agent"] == "OneMoreChapter/0.1.0"


@responses.activate
def test_search_fills_in_missing_fields_and_skips_non_work_results() -> None:
    responses.get(
        openlibrary.SEARCH_URL,
        json={
            "numFound": 3,
            "docs": [
                {"key": "/works/OL1W"},  # only a key: everything else is optional
                {"key": "/authors/OL2A", "title": "Not a book"},
                {"title": "No key at all"},
            ],
        },
    )

    page = openlibrary.search("anything")

    assert page.results == [
        openlibrary.SearchResult(
            work_key="OL1W", title="Untitled", authors=[], first_publish_year=None, cover_id=None
        )
    ]


@responses.activate
def test_other_client_errors_are_bad_responses() -> None:
    """A 400 means we sent something Open Library didn't expect, not that it is down."""
    responses.get(openlibrary.SEARCH_URL, status=400)

    with pytest.raises(openlibrary.OpenLibraryBadResponse):
        openlibrary.search("dune")


@pytest.mark.parametrize(("query", "page"), [("", 1), ("   ", 1), ("dune", 0), ("dune", 51)])
def test_search_refuses_blank_queries_and_out_of_range_pages(query: str, page: int) -> None:
    """These are caller mistakes, caught before any request (the network is blocked here)."""
    with pytest.raises(ValueError):
        openlibrary.search(query, page)


@responses.activate
def test_each_page_is_cached_separately() -> None:
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    openlibrary.search("dune", page=1)
    openlibrary.search("dune", page=2)
    openlibrary.search("dune", page=1)

    assert [call.request.params["page"] for call in responses.calls] == ["1", "2"]


def test_cover_url_builds_open_library_cover_links() -> None:
    assert openlibrary.cover_url(11481354, "L") == (
        "https://covers.openlibrary.org/b/id/11481354-L.jpg?default=false"
    )
    assert openlibrary.cover_url(None) is None


@responses.activate
def test_only_successful_searches_are_cached() -> None:
    """A failed search is retried for real; a successful one is reused for repeats.

    ``responses`` hands out matching fakes in the order they were registered,
    so the first request gets the 503 and the second gets the real results.
    """
    responses.get(openlibrary.SEARCH_URL, status=503)
    responses.get(openlibrary.SEARCH_URL, json=DUNE_RESPONSE)

    with pytest.raises(openlibrary.OpenLibraryUnavailable):
        openlibrary.search("dune")
    first = openlibrary.search("dune")
    repeat = openlibrary.search("  DUNE ")

    assert len(responses.calls) == 2  # the failure + one success; the repeat was cached
    assert repeat.total == first.total == 1
    assert [book.title for book in repeat.results] == ["Dune"]


@pytest.mark.parametrize(
    ("fake_response", "expected_error"),
    [
        ({"body": requests.Timeout()}, openlibrary.OpenLibraryUnavailable),
        ({"body": requests.ConnectionError()}, openlibrary.OpenLibraryUnavailable),
        ({"status": 500}, openlibrary.OpenLibraryUnavailable),
        ({"status": 503}, openlibrary.OpenLibraryUnavailable),
        ({"status": 429}, openlibrary.OpenLibraryUnavailable),
        ({"body": "<html>not json</html>"}, openlibrary.OpenLibraryBadResponse),
        ({"json": {"unexpected": "shape"}}, openlibrary.OpenLibraryBadResponse),
        ({"json": ["a", "list"]}, openlibrary.OpenLibraryBadResponse),
    ],
    ids=[
        "timeout",
        "connection-error",
        "500",
        "503",
        "429",
        "invalid-json",
        "missing-keys",
        "list",
    ],
)
@responses.activate
def test_search_failures_raise_the_right_kind_of_error(
    fake_response: dict, expected_error: type[openlibrary.OpenLibraryError]
) -> None:
    """Outages and rate limits are "unavailable"; unreadable answers are "bad response".

    Callers can catch the base ``OpenLibraryError``, and the exact subclass
    tells them which message (or later, which API status code) to show.
    """
    responses.get(openlibrary.SEARCH_URL, **fake_response)

    with pytest.raises(openlibrary.OpenLibraryError) as excinfo:
        openlibrary.search("dune")

    assert isinstance(excinfo.value, expected_error)
