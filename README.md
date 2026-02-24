# Shelfie — Your Personal Book Recommendation Engine

## Core Principle

**No local book catalog.** Books are ephemeral data fetched live from APIs. The only thing stored locally is *you* — your reading history, your reviews, your recommendation sessions. This keeps the system simple and the data always fresh.

## Quick Start

```bash
# Clone and install
cd myreads
pip install -e .

# Set up your API keys
cp .env.example .env
# Edit .env with your OPENAI_API_KEY (required) and GOOGLE_BOOKS_API_KEY (optional)

# Log some reads
shelfie log "Sapiens"
shelfie log "Project Hail Mary"

# Get recommendations
shelfie recommend --mood "something contemplative about mortality" --direction explore-new

# Browse your history
shelfie list
shelfie recs
```

## Version Roadmap

### V0 — Foundation (current)

Local CLI + TinyDB + ChromaDB + OpenAI. Log reads with ratings/reviews (embedded in ChromaDB for semantic retrieval), fetch book data live from APIs, get LLM-powered recommendations that understand your history, mood, and direction preference.

### V1 — Smarter Loop

- Recommendation feedback (mark recs as "read it", "not interested", "loved it") — feeds back into future prompts
- Goodreads CSV import for bootstrapping reading history
- Reading pattern analysis (auto-detect genres you're gravitating toward or away from)
- Richer prompts with rolling context windows over embedded history

### V2 — Rich Context

- Pull aggregated reviews from multiple sources to feed into recommendation prompts
- Reading lists / shelves (e.g., "want to read", "favorites", "re-read")
- Semantic search over your reading history ("that book about grief and resilience")
- Optional TUI upgrade (using `textual`)

### V3 — Advanced Intelligence

- Reading statistics and insights dashboard
- Export/sync capabilities
- Multi-LLM provider support (Anthropic, local models via Ollama)
- Conversational recommendation mode (back-and-forth refinement)

## Architecture

```
CLI (typer) → Services → APIs (Google Books, Open Library, OpenAI)
                ↓
        Local Storage
    ┌───────────┴───────────┐
    TinyDB (JSON)       ChromaDB (vectors)
    - reads               - review embeddings
    - rec sessions        - semantic search
```

## Configuration

Copy `.env.example` to `.env` and fill in:

- `OPENAI_API_KEY` — required for recommendations and review embeddings
- `GOOGLE_BOOKS_API_KEY` — optional, unauthenticated access works but is rate-limited
- `MYREADS_DATA_DIR` — where your data lives (default: `~/.myreads`)
- `OPENAI_MODEL` — model for recommendations (default: `gpt-4o`)
- `OPENAI_EMBEDDING_MODEL` — model for review embeddings (default: `text-embedding-3-small`)
