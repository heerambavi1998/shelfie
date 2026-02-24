from __future__ import annotations

import httpx

from shelfie.models import BookSearchResult

SEARCH_URL = "https://openlibrary.org/search.json"


def search(query: str, max_results: int = 5) -> list[BookSearchResult]:
    params = {"q": query, "limit": max_results, "fields": "key,title,author_name,isbn,first_publish_year,number_of_pages_median,subject,ratings_average,ratings_count"}
    resp = httpx.get(SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: list[BookSearchResult] = []
    for doc in data.get("docs", []):
        isbns = doc.get("isbn", [])
        isbn_13 = next((i for i in isbns if len(i) == 13), "")
        isbn = isbn_13 or (isbns[0] if isbns else "")

        results.append(
            BookSearchResult(
                title=doc.get("title", "Unknown"),
                author=", ".join(doc.get("author_name", ["Unknown"])),
                isbn=isbn,
                published_date=str(doc.get("first_publish_year", "")),
                page_count=doc.get("number_of_pages_median", 0) or 0,
                categories=(doc.get("subject", []) or [])[:5],
                average_rating=doc.get("ratings_average", 0.0) or 0.0,
                ratings_count=doc.get("ratings_count", 0) or 0,
                source="open_library",
                info_url=f"https://openlibrary.org{doc.get('key', '')}",
            )
        )
    return results


def lookup_isbn(title: str, author: str) -> str | None:
    """Try to find an ISBN for a given title + author."""
    query = f"{title} {author}"
    results = search(query, max_results=1)
    if results and results[0].isbn:
        return results[0].isbn
    return None
