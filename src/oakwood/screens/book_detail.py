"""Book detail screen showing full book information."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from ..database import get_book_by_isbn
from ..models import Book


def _format_book_info(book: Book) -> str:
    """Format full book info as Rich markup text."""
    lines = []

    lines.append(f"[bold]{book.full_title}[/bold]")
    if book.authors:
        lines.append(f"[#8a7e6a]by[/#8a7e6a] {book.authors}")
    lines.append("")

    def add_field(label: str, value: str) -> None:
        if value:
            lines.append(f"[#8a7e6a]{label}:[/#8a7e6a] {value}")

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
            lines.append(f"[#8a7e6a]{c}[/#8a7e6a]")

    if book.description:
        lines.append("")
        lines.append("[#8a7e6a]Description:[/#8a7e6a]")
        desc = book.description[:500]
        if len(book.description) > 500:
            desc += "..."
        lines.append(desc)

    lines.append("")
    status = []
    if book.read:
        status.append("[#6a9a4a]Read[/#6a9a4a]")
    if book.wishlist:
        status.append("[#d4a04a]Wishlist[/#d4a04a]")
    if book.signed:
        status.append("[#d4a04a]Signed[/#d4a04a]")
    if book.number_of_copies > 1:
        status.append(f"{book.number_of_copies} copies")
    if status:
        lines.append(" | ".join(status))

    if book.date_added:
        lines.append(f"[#8a7e6a]Added: {book.date_added}[/#8a7e6a]")

    if book.verified and book.last_verified:
        lines.append(f"[#6a9a4a]Verified: {book.last_verified}[/#6a9a4a]")
    else:
        lines.append("[#8a7e6a]Not verified[/#8a7e6a]")

    return "\n".join(lines)


class BookDetailScreen(Screen):
    """Full book information display."""

    BINDINGS = [
        Binding("v", "verify", "Verify"),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, isbn: str) -> None:
        super().__init__()
        self.isbn = isbn

    def compose(self) -> ComposeResult:
        yield Static("", id="detail-panel")
        yield Footer()

    def on_mount(self) -> None:
        book = get_book_by_isbn(self.app.db, self.isbn)
        if book:
            self._book = book
            self.query_one("#detail-panel").update(_format_book_info(book))
        else:
            self.query_one("#detail-panel").update(f"[#c45a3a]No book found with ISBN: {self.isbn}[/#c45a3a]")
            self._book = None

    def action_verify(self) -> None:
        if self._book:
            from .verify import VerifyScreen
            self.app.push_screen(VerifyScreen(isbn=self.isbn))

    def action_go_back(self) -> None:
        self.app.pop_screen()
