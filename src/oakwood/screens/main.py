"""Main screen with stats, search, and book table."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input
from textual import work

from ..database import get_all_books_by_date, get_book_count, get_shelf_counts, search_books
from ..widgets.book_table import BookTable
from ..widgets.stats_panel import StatsPanel


class MainScreen(Screen):
    """Default screen showing stats, search, and book table."""

    BINDINGS = [
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("i", "import_csv", "Import"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatsPanel()
        yield Input(placeholder="Search by title, author, or ISBN...", id="search-input")
        yield BookTable()
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_data()
        self._focus_table()

    def _focus_table(self) -> None:
        try:
            table = self.query_one(BookTable).query_one(DataTable)
            table.focus()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        """Refresh data when returning from another screen."""
        self._refresh_data()
        self._focus_table()

    def _refresh_data(self) -> None:
        """Load data synchronously from the database."""
        conn = self.app.db
        book_count = get_book_count(conn)
        shelf_counts = get_shelf_counts(conn)
        books = get_all_books_by_date(conn)
        self.query_one(StatsPanel).update_stats(book_count, len(shelf_counts))
        self.query_one(BookTable).load_books(books)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._do_search(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """When Enter is pressed in search, move focus to table."""
        if event.input.id == "search-input":
            self._focus_table()

    @work(exclusive=True, group="search", thread=True)
    def _do_search(self, query: str) -> None:
        conn = self.app.db
        if query.strip():
            books = list(search_books(conn, query.strip()))
        else:
            books = get_all_books_by_date(conn)
        self.app.call_from_thread(self._update_table, books)

    def _update_table(self, books: list) -> None:
        """Update just the book table (used by search worker)."""
        self.query_one(BookTable).load_books(books)

    def on_key(self, event) -> None:
        """Handle Escape from search input to return focus to table."""
        if event.key == "escape":
            focused = self.app.focused
            if isinstance(focused, Input):
                self._focus_table()
                event.prevent_default()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_import_csv(self) -> None:
        from .import_csv import ImportScreen
        self.app.push_screen(ImportScreen())

    def on_book_table_book_selected(self, event: BookTable.BookSelected) -> None:
        from .book_detail import BookDetailScreen
        self.app.push_screen(BookDetailScreen(isbn=event.isbn))

    def action_quit(self) -> None:
        self.app.exit()
