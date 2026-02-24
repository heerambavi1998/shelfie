from __future__ import annotations

from pathlib import Path

import chromadb
from tinydb import Query, TinyDB

from shelfie.config import Settings


class Storage:
    """Manages both TinyDB (structured docs) and ChromaDB (embeddings)."""

    def __init__(self, settings: Settings) -> None:
        settings.ensure_data_dir()
        self._settings = settings

        self._db = TinyDB(str(settings.tinydb_path))
        self._reads_table = self._db.table("reads")
        self._sessions_table = self._db.table("sessions")

        self._chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_path)
        )
        self._reviews_collection = self._chroma_client.get_or_create_collection(
            name="reviews",
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def reads(self) -> TinyDB:
        return self._reads_table

    @property
    def sessions(self) -> TinyDB:
        return self._sessions_table

    @property
    def reviews(self) -> chromadb.Collection:
        return self._reviews_collection

    def insert_read(self, doc: dict) -> int:
        return self._reads_table.insert(doc)

    def get_all_reads(self) -> list[dict]:
        return self._reads_table.all()

    def get_read_by_id(self, read_id: str) -> dict | None:
        q = Query()
        results = self._reads_table.search(q.id == read_id)
        return results[0] if results else None

    def read_exists(self, title: str, author: str) -> bool:
        q = Query()
        results = self._reads_table.search(
            (q.title.test(lambda t: t.lower() == title.lower()))
            & (q.author.test(lambda a: a.lower() == author.lower()))
        )
        return len(results) > 0

    def insert_session(self, doc: dict) -> int:
        return self._sessions_table.insert(doc)

    def get_all_sessions(self) -> list[dict]:
        return self._sessions_table.all()

    def upsert_review_embedding(
        self,
        read_id: str,
        review_text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self._reviews_collection.upsert(
            ids=[read_id],
            documents=[review_text],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def query_similar_reviews(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> dict:
        count = self._reviews_collection.count()
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        n = min(n_results, count)
        return self._reviews_collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
        )
