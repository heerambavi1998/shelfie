# Shelfie — Architecture Reference

## Design Philosophy

**Store the reader, not the books.** Shelfie only persists personal data — your reads, reviews, and recommendation sessions. Book metadata is fetched live from external APIs every time, keeping things simple and always up-to-date.

---

## Project Structure

```
src/shelfie/
├── cli.py                    # Typer CLI — all user-facing commands
├── config.py                 # Settings via pydantic-settings + .env
├── models.py                 # Pydantic models (Read, BookRecommendation, etc.)
├── storage.py                # Dual storage manager (TinyDB + ChromaDB)
├── apis/
│   ├── google_books.py       # Google Books API client
│   ├── open_library.py       # Open Library API client
│   └── openai_client.py      # OpenAI embeddings + Pydantic AI recommendation agent
└── services/
    ├── book_lookup.py         # Multi-API search with fallback
    ├── reads.py               # ReadService — log, list, embed reviews
    └── recommendations.py     # RecommendationEngine — context building + post-filtering
```

---

## Layer Diagram

```mermaid
flowchart TB
    subgraph cli [CLI Layer]
        Log["shelfie log"]
        List["shelfie list"]
        Recommend["shelfie recommend"]
        Recs["shelfie recs"]
        Search["shelfie search"]
        Show["shelfie show"]
    end

    subgraph services [Service Layer]
        ReadService[ReadService]
        RecEngine[RecommendationEngine]
        BookLookup[BookLookup]
    end

    subgraph apis [API Clients]
        GoogleBooks[Google Books API]
        OpenLibrary[Open Library API]
        OpenAIChat["Pydantic AI Agent\n(OpenAI Chat)"]
        OpenAIEmbed["OpenAI Embeddings"]
    end

    subgraph storage [Local Storage]
        TinyDB["TinyDB\n~/.myreads/reads.json"]
        ChromaDB["ChromaDB\n~/.myreads/chroma/"]
    end

    cli --> services
    BookLookup --> GoogleBooks
    BookLookup --> OpenLibrary
    RecEngine --> OpenAIChat
    ReadService --> OpenAIEmbed
    ReadService --> TinyDB
    ReadService --> ChromaDB
    RecEngine --> ChromaDB
    RecEngine --> TinyDB
```

---

## Data Model

### What's stored locally

```mermaid
erDiagram
    reads {
        string id PK
        string title
        string author
        string isbn
        string status "reading | read | did-not-finish"
        int rating "1-5"
        text review
        date started_at
        date finished_at
        datetime created_at
    }

    recommendation_sessions {
        string id PK
        text mood
        string direction "explore-new | go-deeper | balance"
        json recommendations "list of BookRecommendation"
        datetime created_at
    }

    chroma_reviews {
        string doc_id PK
        string read_id FK
        text review_text
        vector embedding
        json metadata "title, author, rating, status"
    }

    reads ||--o| chroma_reviews : "review embedded in"
```

### What's fetched live (never stored)

- Book descriptions, genres, page counts — Google Books / Open Library
- Search results
- External ratings

---

## Key Flows

### `shelfie log "Book Name"`

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant BookLookup
    participant GoogleBooks
    participant ReadService
    participant TinyDB
    participant OpenAI_Embed
    participant ChromaDB

    User->>CLI: shelfie log "Dune"
    CLI->>BookLookup: search("Dune")
    BookLookup->>GoogleBooks: GET /volumes?q=Dune
    GoogleBooks-->>BookLookup: results
    BookLookup-->>CLI: BookSearchResult[]
    CLI->>User: Show matches, ask which one
    User->>CLI: Pick #1, rating, review, status
    CLI->>ReadService: log_read(Read)
    ReadService->>ReadService: Check for duplicates
    ReadService->>TinyDB: insert(read.to_doc())
    ReadService->>OpenAI_Embed: embed(review_text)
    OpenAI_Embed-->>ReadService: vector
    ReadService->>ChromaDB: upsert(id, text, vector, metadata)
    ReadService-->>CLI: Read (saved)
    CLI->>User: Show confirmation panel
```

### `shelfie recommend --mood "..." --direction explore-new`

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant RecEngine
    participant ChromaDB
    participant TinyDB
    participant OpenAI_Embed
    participant PydanticAI

    User->>CLI: shelfie recommend --mood "contemplative"
    CLI->>RecEngine: recommend(mood, direction)

    Note over RecEngine: Phase 1 — Build context
    RecEngine->>TinyDB: get recent 20 reads
    TinyDB-->>RecEngine: reading_history
    RecEngine->>OpenAI_Embed: embed(mood)
    OpenAI_Embed-->>RecEngine: mood_vector
    RecEngine->>ChromaDB: query(mood_vector, n=5)
    ChromaDB-->>RecEngine: semantically relevant reviews

    Note over RecEngine: Phase 2 — Build blocklist
    RecEngine->>TinyDB: get ALL read titles
    RecEngine->>TinyDB: get ALL past rec titles
    TinyDB-->>RecEngine: blocklist (set of normalized titles)

    Note over RecEngine: Phase 3 — Generate + filter
    RecEngine->>PydanticAI: Agent.run_sync(prompt)
    PydanticAI-->>RecEngine: RecommendationResponse (validated Pydantic model)
    RecEngine->>RecEngine: Filter recs against blocklist
    RecEngine->>RecEngine: Retry if < 5 unique recs

    Note over RecEngine: Phase 4 — Persist
    RecEngine->>TinyDB: insert(session.to_doc())
    RecEngine-->>CLI: RecommendationSession
    CLI->>User: Display recs with match types
```

---

## Storage Details

### TinyDB (`~/.myreads/reads.json`)

A single JSON file with two tables:
- **reads** — your reading log
- **sessions** — recommendation session history

Queried using TinyDB's `Query` objects. Duplicate detection uses case-insensitive title + author matching.

### ChromaDB (`~/.myreads/chroma/`)

Persistent vector store with one collection:
- **reviews** — embedded review text with metadata (title, author, rating, status)

Uses cosine similarity. Vectors are generated via OpenAI's `text-embedding-3-small` model. Queried by embedding the user's mood and finding the most semantically relevant past reviews.

---

## Recommendation Strategy

The engine does NOT stuff the prompt with your entire library. Instead:

1. **Lean prompt** — only recent reads (last 20) with reviews go to the LLM for taste understanding
2. **Semantic retrieval** — ChromaDB finds the 5 reviews most relevant to the current mood (even without keyword overlap)
3. **Post-filtering** — after the LLM responds, recommendations are checked against a local blocklist of all reads + all past recs. Duplicates are dropped.
4. **Retry loop** — if filtering removes too many, the engine retries (up to 2x) to fill the gap

This scales to any library size — the blocklist is a `set[str]` in memory, never part of the prompt.

### Pydantic AI Integration

Recommendations use a Pydantic AI `Agent` with `output_type=RecommendationResponse`. This means:
- The LLM is forced to return structured data matching the schema
- Output is automatically validated as a list of `BookRecommendation` objects
- No manual JSON parsing — `result.output.recommendations` gives typed Python objects
- `match_type` (safe bet / stretch pick / wild card) is an enum validated at parse time

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| CLI | `typer` + `rich` | Type-hint based commands, beautiful terminal output |
| Data models | `pydantic` | Validation, serialization, schema generation |
| Config | `pydantic-settings` | `.env` file loading with typed defaults |
| Document store | `tinydb` | Zero-setup JSON-file database |
| Vector store | `chromadb` | Local persistent embeddings with cosine search |
| LLM | `pydantic-ai` | Typed agent with validated structured output |
| Embeddings | `openai` SDK | Review embedding via text-embedding-3-small |
| HTTP | `httpx` | Modern async-capable HTTP client |
| Book data | Google Books + Open Library APIs | Free, no auth required |
