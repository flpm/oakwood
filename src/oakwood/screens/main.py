"""Main screen with stats, search, and book table.

This is the default screen shown on launch. It displays a stats bar, a
search input, and a sortable table of all books. Keys: ``/`` search,
``i`` import, ``a`` about, ``q`` quit, Enter for book details.
"""

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
    """Default screen showing stats, search, and a sortable book table.

    Preserves the cursor position and scroll offset when returning from
    detail/edit screens so the user can continue browsing where they left
    off.
    """

    BINDINGS = [
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("i", "import_csv", "Import"),
        Binding("m", "toggle_mcp_mode", "MCP mode"),
        Binding("a", "about", "About"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Build the screen layout: stats, search input, book table, footer."""
        yield StatsPanel()
        yield Input(placeholder="Search by title, author, or ISBN...", id="search-input")
        yield BookTable()
        yield Footer()

    def on_mount(self) -> None:
        """Load data and focus the book table on first mount."""
        self._refresh_data()
        self._focus_table()

    def _focus_table(self) -> None:
        """Move keyboard focus to the inner ``DataTable``."""
        try:
            table = self.query_one(BookTable).query_one(DataTable)
            table.focus()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        """Refresh data when returning from another screen.

        Preserves the current sort order and restores the cursor to the
        previously selected book.
        """
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
        """Re-query the database and update the stats panel."""
        conn = self.app.db
        book_count = get_book_count(conn)
        shelf_counts = get_shelf_counts(conn)
        last_added = get_last_added_date(conn)
        db_display = self.app._settings.db_path
        self.query_one(StatsPanel).update_stats(
            __version__, db_display, book_count, len(shelf_counts), last_added,
            mcp_mode=self.app.mcp_mode,
        )

    def _refresh_data(self) -> None:
        """Reload stats and all books into the table."""
        self._refresh_stats()
        books = get_all_books_by_date(self.app.db)
        book_table = self.query_one(BookTable)
        book_table.load_books(books)
        self._restore_cursor(book_table)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Trigger a search whenever the search input text changes."""
        if event.input.id == "search-input":
            self._do_search(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Move focus from the search input to the table on Enter."""
        if event.input.id == "search-input":
            self._focus_table()

    @work(exclusive=True, group="search", thread=True)
    def _do_search(self, query: str) -> None:
        """Run a search query in a background thread.

        Parameters
        ----------
        query : str
            The search term entered by the user.
        """
        conn = self.app.db
        if query.strip():
            books = list(search_books(conn, query.strip()))
        else:
            books = get_all_books_by_date(conn)
        self.app.call_from_thread(self._update_table, books)

    def _update_table(self, books: list) -> None:
        """Replace the book table contents (called from the search worker).

        Parameters
        ----------
        books : list of Book
            Search results or full book list.
        """
        book_table = self.query_one(BookTable)
        book_table.load_books(books)
        self._restore_cursor(book_table)

    def _restore_cursor(self, book_table: BookTable) -> None:
        """Restore the cursor and scroll position saved before a screen push.

        Parameters
        ----------
        book_table : BookTable
            The table widget to restore the cursor in.
        """
        isbn = getattr(self, "_resume_isbn", None)
        scroll_y = getattr(self, "_resume_scroll_y", None)
        if isbn:
            book_table.select_by_isbn(isbn, scroll_y=scroll_y)
            self._resume_isbn = None
            self._resume_scroll_y = None

    def on_key(self, event) -> None:
        """Handle Escape: move focus from search to table, or clear search."""
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
        """Focus the search input (bound to ``/``)."""
        self.query_one("#search-input", Input).focus()

    def action_toggle_mcp_mode(self) -> None:
        """Toggle MCP read-only mode (bound to ``m``)."""
        self.app.mcp_mode = not self.app.mcp_mode
        if self.app.mcp_mode:
            self.notify("MCP mode ON — TUI is read-only", severity="warning")
        else:
            self.notify("MCP mode OFF — refreshing data")
            self._refresh_data()
        self._refresh_stats()

    def action_import_csv(self) -> None:
        """Push the CSV import screen (bound to ``i``)."""
        if self.app.mcp_mode:
            self.notify("Import disabled in MCP mode", severity="warning")
            return
        from .import_csv import ImportScreen
        self.app.push_screen(ImportScreen())

    def on_book_table_book_selected(self, event: BookTable.BookSelected) -> None:
        """Open the book detail screen for the selected book.

        Saves the current cursor position so it can be restored on return.
        """
        from .book_detail import BookDetailScreen
        book_table = self.query_one(BookTable)
        self._resume_isbn = event.isbn
        self._resume_scroll_y = book_table.get_scroll_y()
        isbn_list = book_table.get_isbn_list()
        self.app.push_screen(BookDetailScreen(isbn=event.isbn, isbn_list=isbn_list))

    def action_about(self) -> None:
        """Push the about screen (bound to ``a``)."""
        from .about import AboutScreen
        self.app.push_screen(AboutScreen())

    def action_quit(self) -> None:
        """Exit the application (bound to ``q``)."""
        self.app.exit()
