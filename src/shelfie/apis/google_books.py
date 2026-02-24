from __future__ import annotations

import httpx

from shelfie.models import BookSearchResult

BASE_URL = "https://www.googleapis.com/books/v1/volumes"


def search(query: str, api_key: str = "", max_results: int = 5) -> list[BookSearchResult]:
    params: dict = {"q": query, "maxResults": max_results}
    if api_key:
        params["key"] = api_key

    resp = httpx.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: list[BookSearchResult] = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        identifiers = info.get("industryIdentifiers", [])
        isbn = ""
        for ident in identifiers:
            if ident.get("type") == "ISBN_13":
                isbn = ident["identifier"]
                break
            if ident.get("type") == "ISBN_10":
                isbn = ident["identifier"]

        results.append(
            BookSearchResult(
                title=info.get("title", "Unknown"),
                author=", ".join(info.get("authors", ["Unknown"])),
                isbn=isbn,
                description=info.get("description", ""),
                published_date=info.get("publishedDate", ""),
                page_count=info.get("pageCount", 0),
                categories=info.get("categories", []),
                average_rating=info.get("averageRating", 0.0),
                ratings_count=info.get("ratingsCount", 0),
                source="google_books",
                info_url=info.get("infoLink", ""),
            )
        )
    return results


def lookup_isbn(title: str, author: str, api_key: str = "") -> str | None:
    """Try to find an ISBN for a given title + author."""
    query = f'intitle:{title} inauthor:{author}'
    results = search(query, api_key=api_key, max_results=1)
    if results and results[0].isbn:
        return results[0].isbn
    return None
