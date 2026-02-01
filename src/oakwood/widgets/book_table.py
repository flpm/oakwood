"""Book table widget with ISBN tracking."""

from textual.message import Message
from textual.widgets import DataTable, Static


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
        table.add_column("Title", width=self._w_title, key="title")
        table.add_column("Authors", width=self._w_authors, key="authors")
        table.add_column("Shelf", width=w_shelf, key="shelf")
        table.add_column("Added", width=w_added, key="added")

    def load_books(self, books: list) -> None:
        """Populate the table with books."""
        table = self.query_one(DataTable)
        self._ensure_columns()
        table.clear()
        self._isbn_map.clear()
        title_max = getattr(self, "_w_title", 60)
        authors_max = getattr(self, "_w_authors", 30)
        for book in books:
            date_str = str(book.date_added) if book.date_added else ""
            row_key = table.add_row(
                book.display_title(title_max),
                book.display_authors(authors_max),
                book.bookshelf or "",
                date_str,
            )
            self._isbn_map[row_key] = book.isbn

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Forward row selection as BookSelected message."""
        isbn = self._isbn_map.get(event.row_key)
        if isbn:
            self.post_message(self.BookSelected(isbn))

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
