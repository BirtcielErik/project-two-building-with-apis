"""Tests for the Search page. The Open Library service is replaced with fakes."""

import pytest

from shelf import openlibrary


@pytest.fixture
def search_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int]]:
    """Replace ``openlibrary.search`` with a fake and return the list of calls it receives."""
    calls: list[tuple[str, int]] = []

    def fake_search(query: str, page: int = 1) -> openlibrary.SearchPage:
        calls.append((query, page))
        return openlibrary.SearchPage(query=query, page=page, total=0, results=[])

    monkeypatch.setattr(openlibrary, "search", fake_search)
    return calls


def make_book(number: int, cover_id: int | None = 1000) -> openlibrary.SearchResult:
    """Build a fake search result whose fields all include ``number``."""
    return openlibrary.SearchResult(
        work_key=f"OL{number}W",
        title=f"Book {number}",
        authors=[f"Author {number}", "Co Author"],
        first_publish_year=1900 + number,
        cover_id=cover_id,
    )


def fake_search_returning(
    monkeypatch: pytest.MonkeyPatch, total: int, results: list[openlibrary.SearchResult]
) -> list[tuple[str, int]]:
    """Make ``openlibrary.search`` return the given page; return the list of calls it gets."""
    calls: list[tuple[str, int]] = []

    def fake_search(query: str, page: int = 1) -> openlibrary.SearchPage:
        calls.append((query, page))
        return openlibrary.SearchPage(query=query, page=page, total=total, results=results)

    monkeypatch.setattr(openlibrary, "search", fake_search)
    return calls


def fake_search_raising(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    """Make ``openlibrary.search`` fail with ``error``."""

    def fake_search(query: str, page: int = 1) -> openlibrary.SearchPage:
        raise error

    monkeypatch.setattr(openlibrary, "search", fake_search)


HTMX_HEADERS = {"HX-Request": "true"}


@pytest.mark.parametrize(
    ("url", "expected_message"),
    [
        ("/search/?q=", "Type a title, author, or keyword"),
        ("/search/?q=+++", "Type a title, author, or keyword"),
        ("/search/?q=dune&page=51", "Try a more specific search"),
    ],
    ids=["empty", "whitespace-only", "past-page-cap"],
)
def test_search_explains_instead_of_calling_open_library(
    logged_in_client, search_calls, url: str, expected_message: str
) -> None:
    """A blank query gets a hint and a page past 50 gets a nudge; neither calls Open Library."""
    response = logged_in_client.get(url)

    assert response.status_code == 200
    assert expected_message in response.content.decode()
    assert search_calls == []


def test_search_page_before_searching_invites_a_search(logged_in_client, search_calls) -> None:
    html = logged_in_client.get("/search/").content.decode()

    assert "data-search-start" in html
    assert 'name="q"' in html
    assert search_calls == []


def test_results_show_each_book_and_the_total(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=1234, results=[make_book(1), make_book(2)])

    html = logged_in_client.get("/search/?q=dune").content.decode()

    assert "1,234" in html
    assert "Book 1" in html
    assert "Author 1, Co Author" in html
    assert "1901" in html
    assert "Book 2" in html
    assert html.count("data-book-row") == 2


def test_results_show_covers_or_a_placeholder(logged_in_client, monkeypatch) -> None:
    fake_search_returning(
        monkeypatch, total=2, results=[make_book(1, cover_id=555), make_book(2, cover_id=None)]
    )

    html = logged_in_client.get("/search/?q=dune").content.decode()

    assert 'src="https://covers.openlibrary.org/b/id/555-M.jpg?default=false"' in html
    # Both rows have a placeholder; it starts visible only for the book without a cover.
    assert html.count("data-cover-placeholder") == 2
    assert html.count("<img") == 1


def test_query_is_trimmed_and_page_is_passed_to_the_service(logged_in_client, monkeypatch) -> None:
    calls = fake_search_returning(monkeypatch, total=100, results=[make_book(1)])

    logged_in_client.get("/search/?q=++the+++hobbit+&page=3")

    assert calls == [("the hobbit", 3)]


@pytest.mark.parametrize("raw_page", ["abc", "0", "-4", ""])
def test_invalid_page_numbers_fall_back_to_page_one(
    logged_in_client, monkeypatch, raw_page
) -> None:
    calls = fake_search_returning(monkeypatch, total=100, results=[make_book(1)])

    response = logged_in_client.get(f"/search/?q=dune&page={raw_page}")

    assert response.status_code == 200
    assert calls == [("dune", 1)]


def test_htmx_request_gets_only_the_results(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=1, results=[make_book(1)])

    response = logged_in_client.get("/search/?q=dune", headers=HTMX_HEADERS)
    html = response.content.decode()

    assert "Book 1" in html
    assert "<html" not in html
    assert "HX-Request" in response["Vary"]


def test_normal_request_gets_the_full_page_with_results(logged_in_client, monkeypatch) -> None:
    """A bookmarked or reloaded search URL renders the whole page, results included."""
    fake_search_returning(monkeypatch, total=1, results=[make_book(1)])

    html = logged_in_client.get("/search/?q=dune").content.decode()

    assert "<html" in html
    assert 'value="dune"' in html
    assert "Book 1" in html


def test_history_restore_gets_the_full_page(logged_in_client, monkeypatch) -> None:
    """Pressing Back can make HTMX re-request a URL; that needs the full page."""
    fake_search_returning(monkeypatch, total=1, results=[make_book(1)])

    html = logged_in_client.get(
        "/search/?q=dune",
        headers={**HTMX_HEADERS, "HX-History-Restore-Request": "true"},
    ).content.decode()

    assert "<html" in html


def test_pagination_is_shortened_and_keeps_the_query(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=200, results=[make_book(1)])  # 10 pages

    html = logged_in_client.get("/search/?q=dune&page=5").content.decode()

    assert 'aria-current="page">5<' in html
    for linked_page in [1, 4, 6, 10]:
        assert f'href="/search/?q=dune&amp;page={linked_page}"' in html
    for hidden_page in [2, 3, 7, 8, 9]:
        assert f'page={hidden_page}"' not in html
    assert "…" in html


def test_pagination_stops_at_page_fifty(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=99_999, results=[make_book(1)])

    html = logged_in_client.get("/search/?q=the&page=50").content.decode()

    assert "page 50 of 50" in html
    assert "page=51" not in html
    assert "Try a more specific search" in html


def test_single_page_of_results_has_no_pagination(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=3, results=[make_book(1)])

    html = logged_in_client.get("/search/?q=dune").content.decode()

    assert 'aria-label="Pagination"' not in html


def test_no_matches_says_so(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=0, results=[])

    html = logged_in_client.get("/search/?q=zzqqxx").content.decode()

    assert "No books found for “zzqqxx”" in html


def test_page_past_the_last_result_links_back(logged_in_client, monkeypatch) -> None:
    fake_search_returning(monkeypatch, total=45, results=[])  # 3 pages

    html = logged_in_client.get("/search/?q=dune&page=9").content.decode()

    assert "There are no results on this page" in html
    assert 'href="/search/?q=dune&amp;page=3"' in html


@pytest.mark.parametrize(
    ("error", "expected_text"),
    [
        (openlibrary.OpenLibraryUnavailable("down"), "Open Library isn't responding right now."),
        (openlibrary.OpenLibraryBadResponse("junk"), "something we couldn't read"),
    ],
)
def test_open_library_failures_show_a_persistent_alert(
    logged_in_client, monkeypatch, error, expected_text
) -> None:
    fake_search_raising(monkeypatch, error)

    response = logged_in_client.get("/search/?q=dune", headers=HTMX_HEADERS)
    html = response.content.decode()

    # 200, so HTMX swaps the message in (it ignores error status codes by default).
    assert response.status_code == 200
    assert expected_text in html
    assert "Your shelf still works" in html
    assert 'hx-get="/search/?q=dune"' in html  # Try again repeats the same search
    assert "Try again" in html
    assert 'href="/shelf/"' in html


def test_search_page_credits_open_library(logged_in_client) -> None:
    html = logged_in_client.get("/search/").content.decode()

    assert "Book data from" in html
    assert 'href="https://openlibrary.org"' in html
