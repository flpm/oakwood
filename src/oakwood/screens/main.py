"""Main screen with stats, search, and book table."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input
from textual import work

from .. import __version__
from ..database import (
    get_all_books_by_date,
    get_book_count,
    get_last_added_date,
    get_shelf_counts,
    search_books,
)
from ..widgets.book_table import BookTable
from ..widgets.stats_panel import StatsPanel


class MainScreen(Screen):
    """Default screen showing stats, search, and book table."""

    BINDINGS = [
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("i", "import_csv", "Import"),
        Binding("a", "about", "About"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
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
        """Refresh data when returning from another screen, preserving sort order."""
        self._refresh_stats()
        conn = self.app.db
        query = self.query_one("#search-input", Input).value.strip()
        if query:
            books = list(search_books(conn, query))
        else:
            books = get_all_books_by_date(conn)
        book_table = self.query_one(BookTable)
        book_table.refresh_books(books)
        self._restore_cursor(book_table)
        self._focus_table()

    def _refresh_stats(self) -> None:
        """Update the stats panel only."""
        conn = self.app.db
        book_count = get_book_count(conn)
        shelf_counts = get_shelf_counts(conn)
        last_added = get_last_added_date(conn)
        db_display = self.app._settings.db_path
        self.query_one(StatsPanel).update_stats(
            __version__, db_display, book_count, len(shelf_counts), last_added
        )

    def _refresh_data(self) -> None:
        """Load stats and all books."""
        self._refresh_stats()
        books = get_all_books_by_date(self.app.db)
        book_table = self.query_one(BookTable)
        book_table.load_books(books)
        self._restore_cursor(book_table)

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
        book_table = self.query_one(BookTable)
        book_table.load_books(books)
        self._restore_cursor(book_table)

    def _restore_cursor(self, book_table: BookTable) -> None:
        """Restore cursor and scroll position to the previously selected book, if any."""
        isbn = getattr(self, "_resume_isbn", None)
        scroll_y = getattr(self, "_resume_scroll_y", None)
        if isbn:
            book_table.select_by_isbn(isbn, scroll_y=scroll_y)
            self._resume_isbn = None
            self._resume_scroll_y = None

    def on_key(self, event) -> None:
        """Handle Escape: from search input move to table; from table clear search."""
        if event.key == "escape":
            focused = self.app.focused
            if isinstance(focused, Input):
                self._focus_table()
                event.prevent_default()
            elif isinstance(focused, DataTable):
                search_input = self.query_one("#search-input", Input)
                if search_input.value.strip():
                    search_input.value = ""
                    self._refresh_data()
                    event.prevent_default()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_import_csv(self) -> None:
        from .import_csv import ImportScreen
        self.app.push_screen(ImportScreen())

    def on_book_table_book_selected(self, event: BookTable.BookSelected) -> None:
        from .book_detail import BookDetailScreen
        book_table = self.query_one(BookTable)
        self._resume_isbn = event.isbn
        self._resume_scroll_y = book_table.get_scroll_y()
        isbn_list = book_table.get_isbn_list()
        self.app.push_screen(BookDetailScreen(isbn=event.isbn, isbn_list=isbn_list))

    def action_about(self) -> None:
        from .about import AboutScreen
        self.app.push_screen(AboutScreen())

    def action_quit(self) -> None:
        self.app.exit()
