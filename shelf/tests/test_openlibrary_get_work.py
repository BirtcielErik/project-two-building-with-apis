"""Tests for looking up one work by key, faked at the HTTP level with ``responses``."""

import json

import pytest
import requests
import responses

from shelf import openlibrary

HOBBIT_DOC = {
    "key": "/works/OL27482W",
    "title": "The Hobbit",
    "author_name": ["J.R.R. Tolkien"],
    "first_publish_year": 1937,
    "cover_i": 14627509,
}


def fake_open_library(request: requests.PreparedRequest) -> tuple[int, dict, str]:
    """Answer like the real search endpoint does for ``key:`` queries.

    Only the full ``key:/works/<key>`` query finds the book. Anything else (an
    unprefixed key, an unknown key) gets HTTP 200 with zero matches.
    """
    if request.params.get("q") == "key:/works/OL27482W":
        body = {"numFound": 1, "docs": [HOBBIT_DOC]}
    else:
        body = {"numFound": 0, "docs": []}
    return 200, {}, json.dumps(body)


@responses.activate
def test_get_work_adds_the_works_prefix_and_treats_zero_matches_as_not_found() -> None:
    responses.add_callback(responses.GET, openlibrary.SEARCH_URL, callback=fake_open_library)

    book = openlibrary.get_work("OL27482W")

    assert book == openlibrary.SearchResult(
        work_key="OL27482W",
        title="The Hobbit",
        authors=["J.R.R. Tolkien"],
        first_publish_year=1937,
        cover_id=14627509,
    )
    # An unknown key comes back as HTTP 200 with no docs: that must be "not found".
    with pytest.raises(openlibrary.OpenLibraryNotFound):
        openlibrary.get_work("OL999999999W")


@responses.activate
def test_get_work_sends_restricted_fields_and_timeout() -> None:
    responses.get(openlibrary.SEARCH_URL, json={"numFound": 1, "docs": [HOBBIT_DOC]})

    openlibrary.get_work("OL27482W")

    request = responses.calls[0].request
    assert request.params == {
        "q": "key:/works/OL27482W",
        "fields": "key,title,author_name,first_publish_year,cover_i",
        "limit": "1",
    }
    assert request.req_kwargs["timeout"] == 5
    assert request.headers["User-Agent"].startswith("OneMoreChapter/")


@responses.activate
def test_get_work_rejects_a_result_for_a_different_work() -> None:
    other_doc = {**HOBBIT_DOC, "key": "/works/OL1W"}
    responses.get(openlibrary.SEARCH_URL, json={"numFound": 1, "docs": [other_doc]})

    with pytest.raises(openlibrary.OpenLibraryNotFound):
        openlibrary.get_work("OL27482W")


@responses.activate
def test_get_work_is_not_cached() -> None:
    responses.get(openlibrary.SEARCH_URL, json={"numFound": 1, "docs": [HOBBIT_DOC]})

    openlibrary.get_work("OL27482W")
    openlibrary.get_work("OL27482W")

    assert len(responses.calls) == 2


@responses.activate
@pytest.mark.parametrize(
    ("response_kwargs", "expected_error"),
    [
        ({"body": requests.Timeout()}, openlibrary.OpenLibraryUnavailable),
        ({"body": requests.ConnectionError()}, openlibrary.OpenLibraryUnavailable),
        ({"status": 503}, openlibrary.OpenLibraryUnavailable),
        ({"status": 429}, openlibrary.OpenLibraryUnavailable),
        ({"body": "not json"}, openlibrary.OpenLibraryBadResponse),
        ({"json": {"docs": "nope"}}, openlibrary.OpenLibraryBadResponse),
    ],
)
def test_get_work_failures_raise_the_right_error(response_kwargs, expected_error) -> None:
    responses.get(openlibrary.SEARCH_URL, **response_kwargs)

    with pytest.raises(expected_error):
        openlibrary.get_work("OL27482W")
