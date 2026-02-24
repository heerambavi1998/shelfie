from __future__ import annotations

from shelfie.apis import google_books, open_library
from shelfie.models import BookSearchResult


def search_books(query: str, google_api_key: str = "") -> list[BookSearchResult]:
    """Search for books across available APIs, with graceful fallback."""
    results: list[BookSearchResult] = []

    try:
        results = google_books.search(query, api_key=google_api_key)
    except Exception:
        pass

    if not results:
        try:
            results = open_library.search(query)
        except Exception:
            pass

    return results


def resolve_isbn(title: str, author: str, google_api_key: str = "") -> str:
    """Try to find an ISBN for a book via available APIs."""
    try:
        isbn = google_books.lookup_isbn(title, author, api_key=google_api_key)
        if isbn:
            return isbn
    except Exception:
        pass

    try:
        isbn = open_library.lookup_isbn(title, author)
        if isbn:
            return isbn
    except Exception:
        pass

    return ""
