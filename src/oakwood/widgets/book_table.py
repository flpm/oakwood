"""Book table widget with ISBN tracking and sortable columns."""

from datetime import date

from textual.message import Message
from textual.widgets import DataTable, Static

# Column key -> sort key function
_COLUMN_SORT_KEY = {
    "title": lambda b: (b.title or "").lower(),
    "authors": lambda b: (b.authors or "").lower(),
    "shelf": lambda b: (b.bookshelf or "").lower(),
    "added": lambda b: b.date_added if b.date_added is not None else date.min,
}

# Column key -> (base label, sort shortcut key)
_COLUMNS = {
    "title": ("Title", "F1"),
    "authors": ("Authors", "F2"),
    "shelf": ("Shelf", "F3"),
    "added": ("Added", "F4"),
}

# Keyboard key -> column key
_KEY_TO_COLUMN = {info[1].lower(): col for col, info in _COLUMNS.items()}


class BookTable(Static):
    """DataTable wrapper that tracks ISBN per row and emits BookSelected messages."""

    class BookSelected(Message):
        """Emitted when a book row is selected."""

        def __init__(self, isbn: str) -> None:
            self.isbn = isbn
            super().__init__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._isbn_map: dict = {}  # row_key -> isbn
        self._columns_added = False
        self._books: list = []
        self._sort_column: str = "added"
        self._sort_reverse: bool = True  # descending by default

    def compose(self):
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"

    def _ensure_columns(self) -> None:
        """Add columns sized to the terminal width."""
        if self._columns_added:
            return
        self._columns_added = True
        table = self.query_one(DataTable)
        # Use terminal width (available before layout) minus scrollbar
        width = self.app.size.width - 2
        self._w_title = max(30, int(width * 0.40))
        self._w_authors = max(20, int(width * 0.25))
        w_shelf = max(12, int(width * 0.20))
        w_added = max(10, int(width * 0.15))
        table.add_column(self._header("title"), width=self._w_title, key="title")
        table.add_column(self._header("authors"), width=self._w_authors, key="authors")
        table.add_column(self._header("shelf"), width=w_shelf, key="shelf")
        table.add_column(self._header("added"), width=w_added, key="added")

    def _header(self, col_key: str) -> str:
        """Build a column header string with sort key hint and indicator."""
        base, shortcut = _COLUMNS[col_key]
        indicator = ""
        if col_key == self._sort_column:
            indicator = " ▼" if self._sort_reverse else " ▲"
        return f"{base} [{shortcut}]{indicator}"

    def load_books(self, books: list) -> None:
        """Populate the table with books, resetting sort to default (date descending)."""
        self._books = list(books)
        self._sort_column = "added"
        self._sort_reverse = True
        self._sort_and_reload()

    def refresh_books(self, books: list) -> None:
        """Replace book data and re-sort using the current sort column and direction."""
        self._books = list(books)
        self._sort_and_reload()

    def _sort_and_reload(self) -> None:
        """Sort stored books and repopulate the table rows."""
        table = self.query_one(DataTable)
        self._ensure_columns()
        table.clear()
        self._isbn_map.clear()

        key_fn = _COLUMN_SORT_KEY.get(self._sort_column, _COLUMN_SORT_KEY["added"])
        sorted_books = sorted(self._books, key=key_fn, reverse=self._sort_reverse)

        title_max = getattr(self, "_w_title", 60)
        authors_max = getattr(self, "_w_authors", 30)
        for book in sorted_books:
            date_str = str(book.date_added) if book.date_added else ""
            row_key = table.add_row(
                book.display_title(title_max),
                book.display_authors(authors_max),
                book.bookshelf or "",
                date_str,
            )
            self._isbn_map[row_key] = book.isbn

        self._update_column_labels()

    def _update_column_labels(self) -> None:
        """Refresh all column headers with current sort indicator."""
        from rich.text import Text
        from textual.widgets._data_table import ColumnKey

        table = self.query_one(DataTable)
        for col_key in _COLUMNS:
            column = table.columns.get(ColumnKey(col_key))
            if column is not None:
                column.label = Text(self._header(col_key))
        table.refresh()

    def _sort_by(self, col_key: str) -> None:
        """Sort by the given column, toggling direction if already active."""
        if col_key == self._sort_column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_key
            self._sort_reverse = False
        self._sort_and_reload()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort table when a column header is clicked."""
        col_key = str(event.column_key)
        if col_key in _COLUMN_SORT_KEY:
            self._sort_by(col_key)

    def on_key(self, event) -> None:
        """Handle F1-F4 sort shortcuts when the table has focus."""
        col_key = _KEY_TO_COLUMN.get(event.key)
        if col_key is not None and self._books:
            self._sort_by(col_key)
            event.prevent_default()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Forward row selection as BookSelected message."""
        isbn = self._isbn_map.get(event.row_key)
        if isbn:
            self.post_message(self.BookSelected(isbn))

    def get_isbn_list(self) -> list[str]:
        """Return ISBNs in current display order."""
        return list(self._isbn_map.values())

    def get_scroll_y(self) -> float:
        """Return the current vertical scroll offset."""
        return self.query_one(DataTable).scroll_y

    def select_by_isbn(self, isbn: str, scroll_y: float | None = None) -> None:
        """Move the cursor to the row with the given ISBN and optionally restore scroll."""
        table = self.query_one(DataTable)
        for idx, stored_isbn in enumerate(self._isbn_map.values()):
            if stored_isbn == isbn:
                table.move_cursor(row=idx)
                break
        if scroll_y is not None:
            # move_cursor defers auto-scroll via call_after_refresh;
            # schedule our restore after that so it wins.
            table.call_after_refresh(table.scroll_to, y=scroll_y, animate=False)

    def get_selected_isbn(self) -> str | None:
        """Return the ISBN of the currently highlighted row."""
        table = self.query_one(DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)
            # We need the actual RowKey, not the row data
            # Use the ordered keys approach
            for rk, isbn in self._isbn_map.items():
                if table.get_row(rk) == list(row_key) if isinstance(row_key, tuple) else False:
                    return isbn
        # Fallback: iterate through map by index
        keys = list(self._isbn_map.keys())
        if table.cursor_row is not None and 0 <= table.cursor_row < len(keys):
            return self._isbn_map[keys[table.cursor_row]]
        return None
