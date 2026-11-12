"""Search Open Library by keyword and print the top results.

Usage:
    uv run python scripts/search_books.py

Optional: set OPEN_LIBRARY_CONTACT to your email so Open Library can contact
you about your traffic (identified apps get 3 requests/sec instead of 1).
"""

import os
import sys

import requests

SEARCH_URL = "https://openlibrary.org/search.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
REPO_URL = "https://github.com/BirtcielErik/project-two-building-with-apis"
FIELDS = "key,title,author_name,first_publish_year,edition_count,cover_i"
RESULT_LIMIT = 5
TIMEOUT_SECONDS = 10


class OpenLibraryError(Exception):
    """Raised when a search cannot be completed. The message is user-friendly."""


def build_user_agent():
    """Identify this app to Open Library, adding a contact email if one is set."""
    contact = os.environ.get("OPEN_LIBRARY_CONTACT", "").strip()
    details = f"{REPO_URL}; {contact}" if contact else REPO_URL
    return f"BookTracker/0.1 ({details})"


def search_books(query, limit=RESULT_LIMIT):
    """Search Open Library and return (total_found, list_of_book_dicts).

    Raises OpenLibraryError with a readable message if the request fails.
    """
    params = {"q": query, "fields": FIELDS, "limit": limit}
    headers = {"User-Agent": build_user_agent()}

    try:
        response = requests.get(
            SEARCH_URL, params=params, headers=headers, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.Timeout:
        raise OpenLibraryError(
            f"Open Library did not respond within {TIMEOUT_SECONDS} seconds. "
            "Try again in a moment."
        )
    except requests.ConnectionError:
        raise OpenLibraryError(
            "Could not connect to Open Library. Check your internet connection."
        )
    except requests.HTTPError:
        status = response.status_code
        if status == 429:
            message = "Too many requests (429). Wait a few seconds and try again."
        elif status >= 500:
            message = f"Open Library is having trouble ({status}). Try again later."
        else:
            message = f"Open Library rejected the request ({status} {response.reason})."
        raise OpenLibraryError(message)
    except requests.RequestException as error:
        raise OpenLibraryError(f"The request failed: {error}")

    try:
        data = response.json()
    except ValueError:
        raise OpenLibraryError("Open Library returned a response that was not valid JSON.")

    books = [simplify_book(doc) for doc in data.get("docs", [])]
    return data.get("numFound", len(books)), books


def simplify_book(doc):
    """Turn one raw search result into the fields this app cares about."""
    cover_id = doc.get("cover_i")
    return {
        "title": doc.get("title"),
        "authors": doc.get("author_name", []),
        "first_publish_year": doc.get("first_publish_year"),
        "edition_count": doc.get("edition_count"),
        "work_key": doc.get("key"),
        "cover_url": COVER_URL.format(cover_id=cover_id) if cover_id else None,
    }


def display_results(query, total, books):
    """Print search results as numbered blocks."""
    if not books:
        print(f'\nNo books found for "{query}". Check the spelling or try fewer words.')
        return

    print(f'\nFound {total:,} results for "{query}", showing top {len(books)}:\n')
    for number, book in enumerate(books, start=1):
        print(f"{number}. {book['title'] or '(unknown title)'}")
        print(f"   Author(s):       {', '.join(book['authors']) or '(unknown)'}")
        print(f"   First published: {book['first_publish_year'] or '(unknown)'}")
        print(f"   Editions:        {book['edition_count'] or '(unknown)'}")
        print(f"   Work key:        {book['work_key'] or '(unknown)'}")
        print(f"   Cover:           {book['cover_url'] or '(no cover)'}")
        print()


def ask_for_query():
    """Prompt until the user types something that isn't blank."""
    while True:
        query = input("Search for a book: ").strip()
        if query:
            return query
        print("Please type a title, author, or keyword.")


def main():
    try:
        query = ask_for_query()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 1

    try:
        total, books = search_books(query)
    except OpenLibraryError as error:
        print(f"\nError: {error}")
        return 1

    display_results(query, total, books)
    return 0 if books else 1


if __name__ == "__main__":
    sys.exit(main())
