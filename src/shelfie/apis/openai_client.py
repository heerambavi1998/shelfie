from __future__ import annotations

from openai import OpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from shelfie.models import BookRecommendation, RecommendationResponse

RECOMMENDATION_SYSTEM_PROMPT = """\
You are Shelfie, a deeply thoughtful book recommendation engine. You know the user's reading history, their reviews, and what they're in the mood for right now.

Your job is to recommend books that feel *personally* right — not generic bestseller lists. You consider:
- The user's taste patterns (what they rate highly, what themes recur in their reviews)
- Their current mood/ask
- Their direction preference (explore-new, go-deeper, or balance)

Rules:
- Recommend 5 books
- Mix well-known and lesser-known titles
- For "explore-new": actively diverge from recent genres/topics
- For "go-deeper": find books that share the DNA of their favorites
- For "balance": blend familiar comfort with fresh territory
- Each recommendation needs a specific, personal reason tied to their history and mood
- Do NOT recommend any book that appears in the reading history
- Label each recommendation with a match_type:
  - "safe bet": closely aligns with the reader's demonstrated taste
  - "stretch pick": related to their interests but pushes into new territory
  - "wild card": a surprising left-field pick they'd never find on their own
- Include a mix of match types — not all safe bets"""


def get_embeddings(
    texts: list[str],
    api_key: str,
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def get_embedding(
    text: str,
    api_key: str,
    model: str = "text-embedding-3-small",
) -> list[float]:
    return get_embeddings([text], api_key=api_key, model=model)[0]


def generate_recommendations(
    reading_history: str,
    semantic_context: str,
    mood: str,
    direction: str,
    api_key: str,
    model: str = "gpt-4o",
) -> list[BookRecommendation]:
    provider = OpenAIProvider(api_key=api_key)
    llm = OpenAIModel(model, provider=provider)

    agent = Agent(
        llm,
        system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
        output_type=RecommendationResponse,
    )

    user_prompt = f"""## My Reading History (recent, with my reviews)
{reading_history}

## Reviews Most Relevant to My Current Mood
{semantic_context}

## What I'm Looking For Right Now
Mood: {mood}
Direction: {direction}

Give me 5 book recommendations."""

    result = agent.run_sync(user_prompt)
    return result.output.recommendations
