from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shelfie.config import get_settings
from shelfie.models import Direction, Read, ReadStatus
from shelfie.services.book_lookup import search_books
from shelfie.services.reads import ReadService
from shelfie.services.recommendations import RecommendationEngine
from shelfie.storage import Storage

app = typer.Typer(
    name="shelfie",
    help="Your personal book recommendation engine.",
    no_args_is_help=True,
)
console = Console()


def _get_services() -> tuple[ReadService, RecommendationEngine]:
    settings = get_settings()
    storage = Storage(settings)
    return ReadService(storage, settings), RecommendationEngine(storage, settings)


# ── log ──────────────────────────────────────────────────────────────

def _pick_book(results: list) -> int:
    """Display search results and let the user pick one. Returns 0-based index."""
    for i, book in enumerate(results, 1):
        info_parts = []
        if book.author and book.author != "Unknown":
            info_parts.append(book.author)
        if book.published_date:
            info_parts.append(book.published_date)
        if book.page_count:
            info_parts.append(f"{book.page_count}p")
        meta = "  |  ".join(info_parts)

        desc = ""
        if book.description:
            desc = f"\n   [dim]{book.description[:120]}{'...' if len(book.description) > 120 else ''}[/dim]"

        console.print(f"  [magenta]{i}.[/magenta] [bold]{book.title}[/bold]")
        if meta:
            console.print(f"     {meta}")
        if desc:
            console.print(desc)
        console.print()

    while True:
        choice = typer.prompt("Which one?", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                return idx
        except ValueError:
            pass
        console.print(f"[red]Please enter a number between 1 and {len(results)}[/red]")


_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _parse_flexible_date(text: str) -> date | None:
    """Parse dates in flexible formats: 'June 2024', '15-03-2024', '2024-03-15', 'today', etc."""
    text = text.strip().lower()
    if not text:
        return None
    if text == "today":
        return date.today()

    # "June 2024" or "jun 2024"
    parts = text.split()
    if len(parts) == 2:
        month_str, year_str = parts
        month = _MONTH_NAMES.get(month_str)
        if month and year_str.isdigit():
            return date(int(year_str), month, 1)
        # Also try "2024 June"
        month = _MONTH_NAMES.get(year_str)
        if month and month_str.isdigit():
            return date(int(month_str), month, 1)

    # dd-mm-yyyy or dd/mm/yyyy
    for sep in ("-", "/"):
        if sep in text:
            segs = text.split(sep)
            if len(segs) == 3:
                try:
                    if len(segs[0]) == 4:  # yyyy-mm-dd
                        return date(int(segs[0]), int(segs[1]), int(segs[2]))
                    else:  # dd-mm-yyyy
                        return date(int(segs[2]), int(segs[1]), int(segs[0]))
                except (ValueError, IndexError):
                    pass

    return None


@app.command()
def log(
    book_name: Annotated[str, typer.Argument(help="Name of the book to log")],
) -> None:
    """Log a book you've read (or are reading). Just give the book name — we'll handle the rest."""
    read_service, _ = _get_services()
    settings = get_settings()

    # Step 1: Search for the book
    with console.status("Searching for the book..."):
        results = search_books(book_name, google_api_key=settings.google_books_api_key)

    if not results:
        console.print("[red]Couldn't find that book. Try a different name?[/red]")
        raise typer.Exit(1)

    # Step 2: Pick the right match
    if len(results) == 1:
        chosen = results[0]
        console.print(f"\n  Found: [bold]{chosen.title}[/bold] by {chosen.author}")
        if not typer.confirm("Is this the one?", default=True):
            console.print("[dim]Try again with a more specific name.[/dim]")
            raise typer.Exit()
    else:
        console.print(f"\n  Found {len(results)} matches:\n")
        idx = _pick_book(results)
        chosen = results[idx]

    console.print()

    # Step 3: Rating
    while True:
        rating_input = typer.prompt("How would you rate it? (1-5)", default="")
        if not rating_input:
            rating = None
            break
        try:
            rating = int(rating_input)
            if 1 <= rating <= 5:
                break
        except ValueError:
            pass
        console.print("[red]Please enter a number between 1 and 5[/red]")

    # Step 4: Review
    review = typer.prompt("Quick review (Enter to skip)", default="")

    # Step 5: Status
    console.print("\n  [dim]1. read  2. reading  3. did-not-finish[/dim]")
    status_input = typer.prompt("Status", default="1")
    status_map = {"1": ReadStatus.READ, "2": ReadStatus.READING, "3": ReadStatus.DNF,
                  "read": ReadStatus.READ, "reading": ReadStatus.READING,
                  "did-not-finish": ReadStatus.DNF, "dnf": ReadStatus.DNF}
    status = status_map.get(status_input.lower(), ReadStatus.READ)

    # Step 6: When did you finish?
    finished_at = None
    if status in (ReadStatus.READ, ReadStatus.DNF):
        today_str = date.today().strftime("%d-%m-%Y")
        console.print(f"\n  [dim]Accepts: 'June 2024', '15-03-2024', or Enter for today ({today_str})[/dim]")
        date_input = typer.prompt("When did you finish it?", default="today")
        finished_at = _parse_flexible_date(date_input)
        if finished_at is None:
            finished_at = date.today()
            console.print(f"  [dim]Couldn't parse '{date_input}', using today.[/dim]")
    read = Read(
        title=chosen.title,
        author=chosen.author,
        isbn=chosen.isbn,
        status=status,
        rating=rating or 3,
        review=review,
        finished_at=finished_at,
    )

    with console.status("Saving..."):
        try:
            read = read_service.log_read(read)
        except ValueError as e:
            console.print(f"\n[red]{e}[/red]")
            raise typer.Exit(1)

    stars = "★" * read.rating + "☆" * (5 - read.rating)
    console.print()
    console.print(
        Panel(
            f"[bold]{read.title}[/bold] by {read.author}\n"
            f"Rating: {stars}  |  Status: {read.status.value}\n"
            + (f"\n\n[italic]\"{read.review}\"[/italic]" if read.review else ""),
            title="[magenta]Logged[/magenta]",
            border_style="magenta",
        )
    )


# ── list ─────────────────────────────────────────────────────────────

@app.command(name="list")
def list_reads(
    status: Annotated[Optional[ReadStatus], typer.Option("--status", "-s", help="Filter by status")] = None,
    min_rating: Annotated[Optional[int], typer.Option("--min-rating", help="Minimum rating filter", min=1, max=5)] = None,
) -> None:
    """Show your reading history."""
    read_service, _ = _get_services()
    reads = read_service.list_reads(
        status=status.value if status else None,
        min_rating=min_rating,
    )

    if not reads:
        console.print("[dim]No reads found. Use [bold]shelfie log[/bold] to add some.[/dim]")
        return

    table = Table(title="My Reads", show_lines=True)
    table.add_column("Title", style="bold")
    table.add_column("Author")
    table.add_column("Rating", justify="center")
    table.add_column("Status")
    table.add_column("Review", max_width=40)

    for r in reads:
        stars = "★" * r.rating + "☆" * (5 - r.rating)
        review_preview = r.review[:80] + "..." if len(r.review) > 80 else r.review
        table.add_row(r.title, r.author, stars, r.status.value, review_preview)

    console.print(table)


# ── show ─────────────────────────────────────────────────────────────

@app.command()
def show(
    read_id: Annotated[str, typer.Argument(help="Read ID to show details for")],
) -> None:
    """Show details of a specific read."""
    read_service, _ = _get_services()
    read = read_service.get_read(read_id)

    if not read:
        console.print(f"[red]No read found with ID '{read_id}'[/red]")
        raise typer.Exit(1)

    stars = "★" * read.rating + "☆" * (5 - read.rating)
    content = (
        f"[bold]{read.title}[/bold] by {read.author}\n"
        f"Rating: {stars}  |  Status: {read.status.value}\n"
        f"ISBN: {read.isbn or 'N/A'}"
    )
    if read.started_at:
        content += f"\nStarted: {read.started_at.isoformat()}"
    if read.finished_at:
        content += f"\nFinished: {read.finished_at.isoformat()}"
    if read.review:
        content += f"\n\n[italic]\"{read.review}\"[/italic]"
    content += f"\n\n[dim]ID: {read.id} | Logged: {read.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]"

    console.print(Panel(content, border_style="plum1"))


# ── search ───────────────────────────────────────────────────────────

@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query (title, author, topic)")],
) -> None:
    """Search for books via Google Books / Open Library."""
    settings = get_settings()

    with console.status("Searching..."):
        results = search_books(query, google_api_key=settings.google_books_api_key)

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    for i, book in enumerate(results, 1):
        desc_preview = book.description[:200] + "..." if len(book.description) > 200 else book.description
        rating_str = f"{book.average_rating:.1f}/5 ({book.ratings_count} ratings)" if book.average_rating else "No ratings"

        content = (
            f"[bold]{book.title}[/bold] by {book.author}\n"
            f"Published: {book.published_date or 'N/A'}  |  Pages: {book.page_count or 'N/A'}\n"
            f"Rating: {rating_str}\n"
            f"ISBN: {book.isbn or 'N/A'}"
        )
        if book.categories:
            content += f"\nCategories: {', '.join(book.categories)}"
        if desc_preview:
            content += f"\n\n{desc_preview}"
        if book.info_url:
            content += f"\n[dim]{book.info_url}[/dim]"

        console.print(Panel(content, title=f"[hot_pink]#{i}[/hot_pink]", border_style="hot_pink"))


# ── recommend ────────────────────────────────────────────────────────

@app.command()
def recommend(
    mood: Annotated[Optional[str], typer.Option("--mood", "-m", help="What you're in the mood for")] = None,
    direction: Annotated[Direction, typer.Option("--direction", "-d", help="explore-new, go-deeper, or balance")] = Direction.BALANCE,
) -> None:
    """Get personalized book recommendations based on your reading history and mood."""
    _, rec_engine = _get_services()

    if not mood:
        mood = typer.prompt("What are you in the mood for?")
    
    direction_choice = direction
    if direction == Direction.BALANCE and not typer.Context:
        dir_input = typer.prompt(
            "Direction",
            default="balance",
            type=str,
        )
        try:
            direction_choice = Direction(dir_input)
        except ValueError:
            direction_choice = Direction.BALANCE

    console.print()
    console.print(f"[bold]Mood:[/bold] {mood}")
    console.print(f"[bold]Direction:[/bold] {direction_choice.value}")
    console.print()

    with console.status("Thinking about what you should read next..."):
        try:
            session = rec_engine.recommend(mood, direction_choice)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error generating recommendations: {e}[/red]")
            raise typer.Exit(1)

    console.print(
        Panel(
            f"Session [dim]{session.id}[/dim]  |  {len(session.recommendations)} recommendations",
            title="[medium_purple1]Recommendations[/medium_purple1]",
            border_style="medium_purple1",
        )
    )

    for i, rec in enumerate(session.recommendations, 1):
        match_label = _match_type_label(rec.match_type)
        console.print(f"\n  [hot_pink]#{i}[/hot_pink]  [bold]{rec.title}[/bold] by {rec.author}  {match_label}")
        console.print(f"     [dim]{rec.reason}[/dim]")


_MATCH_TYPE_STYLES = {
    "safe bet": ("orchid", "safe bet"),
    "stretch pick": ("medium_purple1", "stretch pick"),
    "wild card": ("hot_pink", "wild card"),
}


def _match_type_label(match_type) -> str:
    val = match_type.value if hasattr(match_type, "value") else str(match_type)
    style, label = _MATCH_TYPE_STYLES.get(val, ("dim", val))
    return f"[{style}]{label}[/{style}]"


# ── recs ─────────────────────────────────────────────────────────────

@app.command()
def recs() -> None:
    """View past recommendation sessions."""
    _, rec_engine = _get_services()
    sessions = rec_engine.get_sessions()

    if not sessions:
        console.print("[dim]No recommendation sessions yet. Use [bold]shelfie recommend[/bold] to get started.[/dim]")
        return

    for session in sessions:
        direction_val = session.direction.value if isinstance(session.direction, Direction) else session.direction
        console.print(f"\n  [dim]{session.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]  [bold]{session.mood}[/bold]  [dim]({direction_val})[/dim]")
        for i, r in enumerate(session.recommendations, 1):
            match_label = _match_type_label(r.match_type)
            console.print(f"    [hot_pink]#{i}[/hot_pink]  {r.title} by {r.author}  {match_label}")


if __name__ == "__main__":
    app()
