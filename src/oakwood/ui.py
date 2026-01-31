"""Rich UI components for Oakwood CLI."""

from typing import Callable, Iterator, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .models import Book

console = Console()

BROWSE_MAX_WIDTH = 80


def _browse_width() -> int:
    return min(console.width, BROWSE_MAX_WIDTH)


def print_success(message: str) -> None:
    """Print a success message with checkmark."""
    console.print(f"[green]✓[/green] {message}")


def print_skip(message: str) -> None:
    """Print a skip message with circle."""
    console.print(f"[dim]○[/dim] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{message}[/dim]")


def create_spinner(message: str):
    """Create a spinner context for long operations."""
    return console.status(f"[dim]{message}[/dim]", spinner="dots")


def print_import_summary(added: int, skipped: int) -> None:
    """Print import summary."""
    total = added + skipped
    if skipped > 0:
        console.print(f"\nImported [bold]{added}[/bold] books ({skipped} skipped)")
    else:
        console.print(f"\nImported [bold]{added}[/bold] books")


def display_book_table(books: Iterator[Book], max_rows: int = 50) -> None:
    """Display books in a table format."""
    table = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
    table.add_column("Title", style="white", no_wrap=False, max_width=50)
    table.add_column("Authors", style="dim", no_wrap=False, max_width=30)
    table.add_column("Shelf", style="cyan", no_wrap=True)

    count = 0
    for book in books:
        table.add_row(
            book.display_title(50),
            book.display_authors(30),
            book.bookshelf,
        )
        count += 1
        if count >= max_rows:
            break

    console.print(table)

    if count == 0:
        print_info("No books found.")
    elif count == max_rows:
        print_info(f"Showing first {max_rows} books. Use --shelf to filter.")


def display_stats(
    total: int, shelf_counts: dict[str, int], format_counts: dict[str, int]
) -> None:
    """Display collection statistics."""
    console.print(f"Collection: [bold]{total}[/bold] books\n")

    if shelf_counts:
        console.print("[dim]By Shelf:[/dim]")
        for shelf, count in shelf_counts.items():
            console.print(f"  {shelf:<20} {count:>4}")
        console.print()

    if format_counts:
        console.print("[dim]By Format:[/dim]")
        for fmt, count in format_counts.items():
            console.print(f"  {fmt:<20} {count:>4}")


def display_book_info(book: Book) -> None:
    """Display detailed book information."""
    lines = []

    def add_field(label: str, value: str, dim_empty: bool = True) -> None:
        if value:
            lines.append(f"[dim]{label}:[/dim] {value}")
        elif not dim_empty:
            lines.append(f"[dim]{label}:[/dim] [dim]-[/dim]")

    lines.append(f"[bold]{book.full_title}[/bold]")
    if book.authors:
        lines.append(f"[dim]by[/dim] {book.authors}")
    lines.append("")

    add_field("ISBN", book.isbn)
    add_field("Shelf", book.bookshelf)
    add_field("Publisher", book.publisher)
    if book.published_at:
        add_field("Published", str(book.published_at))
    add_field("Format", book.format)
    if book.page_count:
        add_field("Pages", str(book.page_count))
    add_field("Language", book.language)

    if book.series:
        lines.append("")
        series_info = book.series
        if book.volume:
            series_info += f" (Vol. {book.volume})"
        add_field("Series", series_info)

    if book.categories:
        lines.append("")
        add_field("Categories", book.categories)

    contributors = []
    if book.editors:
        contributors.append(f"Editors: {book.editors}")
    if book.translators:
        contributors.append(f"Translators: {book.translators}")
    if book.illustrators:
        contributors.append(f"Illustrators: {book.illustrators}")
    if contributors:
        lines.append("")
        for c in contributors:
            lines.append(f"[dim]{c}[/dim]")

    if book.description:
        lines.append("")
        lines.append("[dim]Description:[/dim]")
        # Wrap description text
        desc = book.description[:500]
        if len(book.description) > 500:
            desc += "..."
        lines.append(desc)

    lines.append("")
    status = []
    if book.read:
        status.append("[green]Read[/green]")
    if book.wishlist:
        status.append("[yellow]Wishlist[/yellow]")
    if book.signed:
        status.append("[cyan]Signed[/cyan]")
    if book.number_of_copies > 1:
        status.append(f"{book.number_of_copies} copies")
    if status:
        lines.append(" | ".join(status))

    if book.date_added:
        lines.append(f"[dim]Added: {book.date_added}[/dim]")

    # Verification status
    if book.verified and book.last_verified:
        lines.append(f"[green]Verified: {book.last_verified}[/green]")
    else:
        lines.append("[dim]Not verified[/dim]")

    panel = Panel(
        "\n".join(lines),
        title="[dim]Book Details[/dim]",
        title_align="left",
        border_style="dim",
        width=_browse_width(),
        padding=(1, 2),
    )
    console.print(panel)


def display_book_summary(book: Book, index: int, total: int) -> None:
    """Display a compact book summary for browse mode."""
    lines = []
    lines.append(f"[bold]{book.full_title}[/bold]")
    if book.authors:
        lines.append(f"[dim]by[/dim] {book.authors}")
    lines.append("")

    details = []
    if book.bookshelf:
        details.append(book.bookshelf)
    if book.format:
        details.append(book.format)
    if book.page_count:
        details.append(f"{book.page_count} pages")
    if details:
        lines.append("[dim]" + "  ·  ".join(details) + "[/dim]")

    if book.date_added:
        lines.append(f"[dim]Added: {book.date_added}[/dim]")

    if book.description:
        lines.append("")
        desc = book.description[:300]
        if len(book.description) > 300:
            desc += "..."
        lines.append(desc)

    panel = Panel(
        "\n".join(lines),
        title=f"[dim]Book {index} of {total}[/dim]",
        title_align="left",
        border_style="dim",
        width=_browse_width(),
        padding=(1, 2),
    )
    console.print(panel)


def browse_prompt() -> str:
    """Show navigation prompt for browse mode and return user choice."""
    console.print(
        "[dim]\[n] Next  \[p] Previous  \[f] +10  \[b] -10  \[d] Details  \[q] Quit[/dim]",
        width=_browse_width(),
    )
    while True:
        choice = Prompt.ask("[dim]Navigate[/dim]", default="n")
        if choice.lower() in ("n", "p", "f", "b", "d", "q"):
            return choice.lower()
        console.print("[dim]Invalid choice. Use n, p, f, b, d, or q.[/dim]")


def interactive_menu(
    options: list[tuple[str, str, str]],
    header: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """Display an interactive menu and return the selected option key.

    Args:
        options: List of (key, shortcut, label) tuples
        header: Optional callback to print a header after clearing the screen

    Returns:
        The selected key or None if user quits
    """
    console.clear()
    if header:
        header()
    shortcuts: dict[str, str] = {}
    console.print()
    for key, shortcut, label in options:
        shortcuts[shortcut] = key
        console.print(f"  [dim]\\[{shortcut}][/dim] {label}")
    console.print(f"  [dim]\\[q][/dim] Quit")
    console.print()

    while True:
        choice = Prompt.ask("[dim]Select[/dim]", default="q")

        if choice.lower() == "q":
            return None

        if choice.lower() in shortcuts:
            return shortcuts[choice.lower()]

        console.print("[dim]Invalid choice[/dim]")


def prompt_search() -> str:
    """Prompt for a search query."""
    return Prompt.ask("[dim]Search[/dim]")


def prompt_isbn() -> str:
    """Prompt for an ISBN."""
    return Prompt.ask("[dim]ISBN[/dim]")


def prompt_shelf(shelves: list[str]) -> Optional[str]:
    """Prompt to select a shelf."""
    if not shelves:
        print_info("No shelves found.")
        return None

    console.print()
    console.print("[dim]Available shelves:[/dim]")
    for i, shelf in enumerate(shelves, 1):
        console.print(f"  [dim]{i}.[/dim] {shelf}")
    console.print(f"  [dim]a.[/dim] All shelves")
    console.print()

    while True:
        choice = Prompt.ask("[dim]Select shelf[/dim]", default="a")

        if choice.lower() == "a":
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(shelves):
                return shelves[idx]
        except ValueError:
            # Check if they typed the shelf name
            for shelf in shelves:
                if choice.lower() == shelf.lower():
                    return shelf

        console.print("[dim]Invalid choice[/dim]")


def display_comparison_table(
    differences: list[tuple[str, str, str]], book_title: str
) -> None:
    """Display a comparison table of local vs API values.

    Args:
        differences: List of (field_name, local_value, api_value) tuples
        book_title: Title of the book being compared
    """
    console.print(f"\nComparing: [bold]{book_title}[/bold]\n")

    table = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Local", style="white", no_wrap=False, max_width=35)
    table.add_column("Open Library", style="yellow", no_wrap=False, max_width=35)

    for field, local_val, api_val in differences:
        # Display field name in a readable format
        display_field = field.replace("_", " ").title()
        table.add_row(
            display_field,
            str(local_val) if local_val else "[dim]-[/dim]",
            str(api_val) if api_val else "[dim]-[/dim]",
        )

    console.print(table)
    console.print()


def prompt_field_choice(field: str, local_val: str, api_val: str) -> str:
    """Prompt user to choose between local and API value.

    Args:
        field: Field name
        local_val: Current local value
        api_val: Value from API

    Returns:
        '1' for keep local, '2' for use API, 's' for skip, 'q' for quit
    """
    display_field = field.replace("_", " ").title()
    console.print(f"[bold]Field: {display_field}[/bold]")
    console.print(f"  [dim]1.[/dim] Keep local:  \"{local_val or '-'}\"")
    console.print(f"  [dim]2.[/dim] Use API:     \"{api_val or '-'}\"")
    console.print(f"  [dim]s.[/dim] Skip")
    console.print(f"  [dim]q.[/dim] Quit")
    console.print()

    while True:
        choice = Prompt.ask("[dim]Select[/dim]", default="s")
        if choice.lower() in ("1", "2", "s", "q"):
            return choice.lower()
        console.print("[dim]Invalid choice. Use 1, 2, s, or q.[/dim]")


def display_verification_summary(
    updated: list[str], skipped: list[str], verified_date: str
) -> None:
    """Display verification summary.

    Args:
        updated: List of field names that were updated
        skipped: List of field names that were skipped
        verified_date: Date the book was marked as verified
    """
    console.print("\n[bold]Verification complete:[/bold]")
    if updated:
        console.print(f"  [green]Updated:[/green] {', '.join(updated)}")
    if skipped:
        console.print(f"  [dim]Skipped:[/dim] {', '.join(skipped)}")
    console.print(f"  Marked as verified on {verified_date}")
