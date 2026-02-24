<p align="center">
  <img src="https://em-content.zobj.net/source/apple/391/books_1f4da.png" width="120" />
</p>

<h1 align="center">Shelfie</h1>
<p align="center"><em>Your personal book recommendation engine that actually gets you.</em></p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-purple?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-OpenAI-ff69b4?style=flat-square&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/storage-local--only-blueviolet?style=flat-square" />
  <img src="https://img.shields.io/badge/vibes-immaculate-hotpink?style=flat-square" />
</p>

---

## 💡 The Idea

Generic book recommendations suck. "People who bought X also bought Y" doesn't know that you just finished three heavy non-fiction books and desperately need a light, weird novel. Or that you want to go *deeper* into Japanese literature after falling in love with Murakami.

**Shelfie knows.** It stores your reading history, embeds your reviews for semantic search, and uses an LLM to generate recommendations that feel *personally* right — based on your mood, your taste, and which direction you want to go.

> 📚 No local book catalog. Books are fetched live from APIs.
> The only thing stored locally is *you* — your reads, your reviews, your vibe.

---

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Set up your API keys
cp .env.example .env
# Edit .env with your OPENAI_API_KEY (required)

# Start logging your reads ✨
shelfie log "Sapiens"
shelfie log "Project Hail Mary"

# Get recommendations that actually fit
shelfie recommend --mood "something contemplative about mortality" --direction explore-new
```

---

## ✏️ Commands

| Command | What it does |
|---|---|
| `shelfie log "Book Name"` | 📖 Conversational flow — searches, confirms, asks for rating + review |
| `shelfie list` | 📋 Show your reading history with stars and reviews |
| `shelfie show <id>` | 🔍 Details on a specific read |
| `shelfie search "query"` | 🌐 Live search Google Books / Open Library |
| `shelfie recommend` | 🔮 Get 5 personalized recs based on history + mood |
| `shelfie recs` | 📜 View past recommendation sessions |

### 🎯 The `--direction` Flag

This is the secret sauce:

- **`explore-new`** — *"I've read enough sci-fi, surprise me"*
- **`go-deeper`** — *"More like the last book I loved"*
- **`balance`** — *A mix of comfort and discovery (default)*

### 🏷️ Match Types

Each recommendation is labeled:

- **safe bet** — closely matches your demonstrated taste
- **stretch pick** — related but pushes your boundaries
- **wild card** — a surprising left-field pick you'd never find on your own

---

## 🏗️ How It Works

```
                    ┌──────────────┐
                    │  shelfie CLI │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Read    │ │  Rec     │ │  Book    │
        │  Service │ │  Engine  │ │  Lookup  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
     ┌───────┴───────┐    │    ┌───────┴────────┐
     ▼               ▼    │    ▼                ▼
 ┌────────┐   ┌─────────┐ │ ┌──────────┐ ┌───────────┐
 │ TinyDB │   │ChromaDB │ │ │ Google   │ │ Open      │
 │ (JSON) │   │(vectors)│ │ │ Books API│ │ Library   │
 └────────┘   └─────────┘ │ └──────────┘ └───────────┘
                           │
                    ┌──────┴───────┐
                    │   OpenAI     │
                    │ (recs +      │
                    │  embeddings) │
                    └──────────────┘
```

**What's stored locally (just you):**
- 📝 Your reads — title, author, ISBN, rating, review, dates
- 🧠 Your review embeddings — for semantic "vibe matching"
- 📜 Your recommendation sessions — mood, direction, results

**What's fetched live (never stored):**
- 📖 Book metadata, descriptions, covers
- ⭐ External ratings and reviews
- 🔍 Search results

---

## 🗺️ Roadmap

| Version | Theme | Highlights |
|---|---|---|
| **V0** ✅ | Foundation | CLI, TinyDB + ChromaDB, OpenAI recs, semantic review matching |
| **V1** 🔜 | Smarter Loop | Rec feedback, Goodreads import, reading pattern analysis |
| **V2** | Rich Context | Multi-source reviews, shelves, semantic history search, TUI |
| **V3** | Advanced | Stats dashboard, multi-LLM, conversational refinement |

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```env
OPENAI_API_KEY=sk-...              # 🔑 required
GOOGLE_BOOKS_API_KEY=...           # 📚 optional (works without, just rate-limited)
MYREADS_DATA_DIR=~/.myreads        # 📁 where your data lives
OPENAI_MODEL=gpt-4o               # 🤖 model for recs
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 🧬 model for review embeddings
```

---

<p align="center">
  <em>Built with 💜 for readers who want more than bestseller lists.</em>
</p>
