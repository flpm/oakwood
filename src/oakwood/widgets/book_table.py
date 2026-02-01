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

    def compose(self):
        yield DataTable()

    def on_mount(self) -> None:
        self._isbn_map: dict = {}  # row_key -> isbn
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Authors", "Shelf", "Added")

    def load_books(self, books: list) -> None:
        """Populate the table with books. Each book must have isbn, title, authors, bookshelf, date_added."""
        table = self.query_one(DataTable)
        table.clear()
        self._isbn_map.clear()
        for book in books:
            date_str = str(book.date_added) if book.date_added else ""
            row_key = table.add_row(
                book.display_title(60),
                book.display_authors(30),
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
