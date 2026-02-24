from __future__ import annotations

from shelfie.apis import openai_client
from shelfie.config import Settings
from shelfie.models import (
    BookRecommendation,
    Direction,
    Read,
    RecommendationSession,
)
from shelfie.storage import Storage

MAX_RETRIES = 1


class RecommendationEngine:
    def __init__(self, storage: Storage, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    def recommend(self, mood: str, direction: Direction) -> RecommendationSession:
        if not self._settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for recommendations.")

        reading_history = self._build_reading_history()
        semantic_context = self._build_semantic_context(mood)
        blocklist = self._build_blocklist()

        filtered_recs: list[BookRecommendation] = []
        for attempt in range(MAX_RETRIES + 1):
            recs = openai_client.generate_recommendations(
                reading_history=reading_history,
                semantic_context=semantic_context,
                mood=mood,
                direction=direction.value,
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
            )

            for rec in recs:
                if not self._is_blocked(rec, blocklist):
                    filtered_recs.append(rec)
                    blocklist.add(self._normalize(rec.title))

            if len(filtered_recs) >= 5 or attempt == MAX_RETRIES:
                break

        session = RecommendationSession(
            mood=mood,
            direction=direction,
            recommendations=filtered_recs[:5],
        )
        self._storage.insert_session(session.to_doc())
        return session

    def get_sessions(self) -> list[RecommendationSession]:
        docs = self._storage.get_all_sessions()
        sessions = [RecommendationSession.from_doc(d) for d in docs]
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions

    def _build_reading_history(self) -> str:
        docs = self._storage.get_all_reads()
        reads = [Read.from_doc(d) for d in docs]
        reads.sort(key=lambda r: r.created_at, reverse=True)

        recent = reads[:20]
        if not recent:
            return "No reading history yet."

        lines: list[str] = []
        for r in recent:
            line = f"- {r.title} by {r.author} | Rating: {r.rating}/5 | Status: {r.status.value}"
            if r.review:
                preview = r.review[:150] + ("..." if len(r.review) > 150 else "")
                line += f'\n  Review: "{preview}"'
            lines.append(line)
        return "\n".join(lines)

    def _build_semantic_context(self, mood: str) -> str:
        """Query ChromaDB for reviews semantically related to the current mood."""
        try:
            mood_embedding = openai_client.get_embedding(
                mood,
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_embedding_model,
            )
        except Exception:
            return "No semantic context available."

        results = self._storage.query_similar_reviews(
            query_embedding=mood_embedding,
            n_results=5,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            return "No relevant past reviews found."

        lines: list[str] = []
        for doc, meta in zip(documents, metadatas):
            title = meta.get("title", "Unknown") if meta else "Unknown"
            rating = meta.get("rating", "?") if meta else "?"
            lines.append(f"[{title}, rated {rating}/5]\n{doc}")
        return "\n\n".join(lines)

    def _build_blocklist(self) -> set[str]:
        """Build a set of normalized titles from all reads + past recommendations."""
        blocked: set[str] = set()

        for doc in self._storage.get_all_reads():
            read = Read.from_doc(doc)
            blocked.add(self._normalize(read.title))

        for doc in self._storage.get_all_sessions():
            session = RecommendationSession.from_doc(doc)
            for rec in session.recommendations:
                blocked.add(self._normalize(rec.title))

        return blocked

    @staticmethod
    def _normalize(title: str) -> str:
        return title.lower().strip()

    def _is_blocked(self, rec: BookRecommendation, blocklist: set[str]) -> bool:
        return self._normalize(rec.title) in blocklist
