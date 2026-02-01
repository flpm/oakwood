"""Browse screen for navigating books one at a time."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Static

from ..database import get_all_books_by_date
from ..models import Book


def _format_book_summary(book: Book) -> str:
    """Format a compact book summary as Rich markup."""
    lines = []
    lines.append(f"[bold]{book.full_title}[/bold]")
    if book.authors:
        lines.append(f"[#8a7e6a]by[/#8a7e6a] {book.authors}")
    lines.append("")

    details = []
    if book.bookshelf:
        details.append(book.bookshelf)
    if book.format:
        details.append(book.format)
    if book.page_count:
        details.append(f"{book.page_count} pages")
    if details:
        lines.append("[#8a7e6a]" + "  ·  ".join(details) + "[/#8a7e6a]")

    if book.date_added:
        lines.append(f"[#8a7e6a]Added: {book.date_added}[/#8a7e6a]")

    if book.description:
        lines.append("")
        desc = book.description[:300]
        if len(book.description) > 300:
            desc += "..."
        lines.append(desc)

    return "\n".join(lines)


class BrowseScreen(Screen):
    """Single-book browse view with keyboard navigation."""

    BINDINGS = [
        Binding("n", "next_book", "Next"),
        Binding("p", "prev_book", "Previous"),
        Binding("f", "forward_10", "+10"),
        Binding("b", "back_10", "-10"),
        Binding("d", "details", "Details"),
        Binding("escape", "go_back", "Back"),
    ]

    index = reactive(0)

    def __init__(self, start_isbn: str | None = None) -> None:
        super().__init__()
        self._start_isbn = start_isbn
        self._books: list[Book] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="browse-counter")
        yield Static("", id="browse-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._books = get_all_books_by_date(self.app.db)
        if not self._books:
            self.query_one("#browse-panel").update("[#8a7e6a]No books in collection.[/#8a7e6a]")
            return

        # Find start index by ISBN if provided
        if self._start_isbn:
            for i, book in enumerate(self._books):
                if book.isbn == self._start_isbn:
                    self.index = i
                    break

        self._render_current()

    def watch_index(self, value: int) -> None:
        if self._books:
            self._render_current()

    def _render_current(self) -> None:
        book = self._books[self.index]
        total = len(self._books)
        self.query_one("#browse-counter").update(
            f"[#8a7e6a]Book {self.index + 1} of {total}[/#8a7e6a]"
        )
        self.query_one("#browse-panel").update(_format_book_summary(book))

    def action_next_book(self) -> None:
        if self._books:
            self.index = min(self.index + 1, len(self._books) - 1)

    def action_prev_book(self) -> None:
        if self._books:
            self.index = max(self.index - 1, 0)

    def action_forward_10(self) -> None:
        if self._books:
            self.index = min(self.index + 10, len(self._books) - 1)

    def action_back_10(self) -> None:
        if self._books:
            self.index = max(self.index - 10, 0)

    def action_details(self) -> None:
        if self._books:
            from .book_detail import BookDetailScreen
            book = self._books[self.index]
            self.app.push_screen(BookDetailScreen(isbn=book.isbn))

    def action_go_back(self) -> None:
        self.app.pop_screen()
