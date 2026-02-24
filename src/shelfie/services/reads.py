from __future__ import annotations

from shelfie.apis import openai_client
from shelfie.config import Settings
from shelfie.models import Read
from shelfie.services.book_lookup import resolve_isbn
from shelfie.storage import Storage


class ReadService:
    def __init__(self, storage: Storage, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def log_read(self, read: Read) -> Read:
        if self._storage.read_exists(read.title, read.author):
            raise ValueError(
                f"You've already logged '{read.title}' by {read.author}."
            )

        if not read.isbn:
            read.isbn = resolve_isbn(
                read.title,
                read.author,
                google_api_key=self._settings.google_books_api_key,
            )

        self._storage.insert_read(read.to_doc())

        if read.review:
            self._embed_review(read)

        return read

    def list_reads(
        self,
        status: str | None = None,
        min_rating: int | None = None,
    ) -> list[Read]:
        docs = self._storage.get_all_reads()
        reads = [Read.from_doc(d) for d in docs]

        if status:
            reads = [r for r in reads if r.status.value == status]
        if min_rating is not None:
            reads = [r for r in reads if r.rating >= min_rating]

        reads.sort(key=lambda r: r.created_at, reverse=True)
        return reads

    def get_read(self, read_id: str) -> Read | None:
        doc = self._storage.get_read_by_id(read_id)
        return Read.from_doc(doc) if doc else None

    def _embed_review(self, read: Read) -> None:
        if not self._settings.openai_api_key:
            return

        text = f"Book: {read.title} by {read.author}\nRating: {read.rating}/5\nReview: {read.review}"
        embedding = openai_client.get_embedding(
            text,
            api_key=self._settings.openai_api_key,
            model=self._settings.openai_embedding_model,
        )
        metadata = {
            "title": read.title,
            "author": read.author,
            "rating": read.rating,
            "status": read.status.value,
        }
        self._storage.upsert_review_embedding(
            read_id=read.id,
            review_text=text,
            embedding=embedding,
            metadata=metadata,
        )
