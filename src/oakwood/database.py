"""SQLite database operations for Oakwood catalogue.

Provides functions for creating, reading, updating, and searching books
in the SQLite database. Uses ISBN as the unique identifier for
deduplication. The connection is created with ``check_same_thread=False``
for Textual worker thread compatibility.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterator, Optional

from .models import Book

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "oakwood.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection, creating the database file if needed.

    Parameters
    ----------
    db_path : Path, optional
        Path to the database file. Defaults to ``DEFAULT_DB_PATH``.

    Returns
    -------
    sqlite3.Connection
        A connection with ``row_factory`` set to ``sqlite3.Row``.
    """
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the books table and indexes if they do not exist.

    Also runs migrations to add any columns introduced after the initial
    schema (e.g. ``verified``, ``last_verified``).

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id TEXT PRIMARY KEY,
            isbn TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            bookshelf TEXT NOT NULL,
            date_added TEXT,
            wishlist INTEGER DEFAULT 0,
            read INTEGER DEFAULT 0,
            pages_read INTEGER DEFAULT 0,
            number_of_copies INTEGER DEFAULT 1,
            signed INTEGER DEFAULT 0,
            authors TEXT DEFAULT '',
            language TEXT DEFAULT '',
            published_at TEXT,
            publisher TEXT DEFAULT '',
            page_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            categories TEXT DEFAULT '',
            format TEXT DEFAULT '',
            subtitle TEXT DEFAULT '',
            series TEXT DEFAULT '',
            volume TEXT DEFAULT '',
            editors TEXT DEFAULT '',
            translators TEXT DEFAULT '',
            illustrators TEXT DEFAULT '',
            verified INTEGER DEFAULT 0,
            last_verified TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_isbn ON books(isbn)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookshelf ON books(bookshelf)")

    # Migration: add verification columns if they don't exist
    cursor = conn.execute("PRAGMA table_info(books)")
    columns = {row[1] for row in cursor.fetchall()}
    if "verified" not in columns:
        conn.execute("ALTER TABLE books ADD COLUMN verified INTEGER DEFAULT 0")
    if "last_verified" not in columns:
        conn.execute("ALTER TABLE books ADD COLUMN last_verified TEXT")

    conn.commit()


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse an ISO-format date string.

    Parameters
    ----------
    date_str : str or None
        A date string in ``YYYY-MM-DD`` format, or ``None``.

    Returns
    -------
    date or None
        The parsed date, or ``None`` if the input is empty or invalid.
    """
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def _row_to_book(row: sqlite3.Row) -> Book:
    """Convert a database row to a Book instance.

    Parameters
    ----------
    row : sqlite3.Row
        A row from the ``books`` table.

    Returns
    -------
    Book
        A populated ``Book`` dataclass instance.
    """
    return Book(
        book_id=row["book_id"],
        isbn=row["isbn"],
        title=row["title"],
        bookshelf=row["bookshelf"],
        date_added=_parse_date(row["date_added"]),
        wishlist=bool(row["wishlist"]),
        read=bool(row["read"]),
        pages_read=row["pages_read"],
        number_of_copies=row["number_of_copies"],
        signed=bool(row["signed"]),
        authors=row["authors"] or "",
        language=row["language"] or "",
        published_at=_parse_date(row["published_at"]),
        publisher=row["publisher"] or "",
        page_count=row["page_count"],
        description=row["description"] or "",
        categories=row["categories"] or "",
        format=row["format"] or "",
        subtitle=row["subtitle"] or "",
        series=row["series"] or "",
        volume=row["volume"] or "",
        editors=row["editors"] or "",
        translators=row["translators"] or "",
        illustrators=row["illustrators"] or "",
        verified=bool(row["verified"]) if row["verified"] is not None else False,
        last_verified=_parse_date(row["last_verified"]),
    )


def book_exists(conn: sqlite3.Connection, isbn: str) -> bool:
    """Check whether a book with the given ISBN exists.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    isbn : str
        The ISBN to look up.

    Returns
    -------
    bool
        ``True`` if a matching row exists.
    """
    cursor = conn.execute("SELECT 1 FROM books WHERE isbn = ?", (isbn,))
    return cursor.fetchone() is not None


def insert_book(conn: sqlite3.Connection, book: Book) -> None:
    """Insert a book row into the database.

    The caller is responsible for committing the transaction.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    book : Book
        The book to insert.
    """
    conn.execute(
        """
        INSERT INTO books (
            book_id, isbn, title, bookshelf, date_added,
            wishlist, read, pages_read, number_of_copies, signed,
            authors, language, published_at, publisher, page_count,
            description, categories, format,
            subtitle, series, volume,
            editors, translators, illustrators,
            verified, last_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            book.book_id,
            book.isbn,
            book.title,
            book.bookshelf,
            book.date_added.isoformat() if book.date_added else None,
            int(book.wishlist),
            int(book.read),
            book.pages_read,
            book.number_of_copies,
            int(book.signed),
            book.authors,
            book.language,
            book.published_at.isoformat() if book.published_at else None,
            book.publisher,
            book.page_count,
            book.description,
            book.categories,
            book.format,
            book.subtitle,
            book.series,
            book.volume,
            book.editors,
            book.translators,
            book.illustrators,
            int(book.verified),
            book.last_verified.isoformat() if book.last_verified else None,
        ),
    )


def get_all_books(
    conn: sqlite3.Connection, shelf: Optional[str] = None
) -> Iterator[Book]:
    """Yield all books, optionally filtered by shelf.

    Results are ordered alphabetically by title.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    shelf : str, optional
        If provided, only return books on this shelf.

    Yields
    ------
    Book
        Books matching the filter criteria.
    """
    if shelf:
        cursor = conn.execute(
            "SELECT * FROM books WHERE bookshelf = ? ORDER BY title", (shelf,)
        )
    else:
        cursor = conn.execute("SELECT * FROM books ORDER BY title")
    for row in cursor:
        yield _row_to_book(row)


def get_book_by_isbn(conn: sqlite3.Connection, isbn: str) -> Optional[Book]:
    """Look up a single book by ISBN.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    isbn : str
        The ISBN to look up.

    Returns
    -------
    Book or None
        The matching book, or ``None`` if not found.
    """
    cursor = conn.execute("SELECT * FROM books WHERE isbn = ?", (isbn,))
    row = cursor.fetchone()
    if row:
        return _row_to_book(row)
    return None


def get_book_count(conn: sqlite3.Connection) -> int:
    """Return the total number of books in the database.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    int
        Total book count.
    """
    cursor = conn.execute("SELECT COUNT(*) FROM books")
    return cursor.fetchone()[0]


def get_shelf_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return book counts grouped by shelf, ordered by count descending.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    dict of str to int
        Mapping of shelf name to book count.
    """
    cursor = conn.execute(
        "SELECT bookshelf, COUNT(*) as count FROM books GROUP BY bookshelf ORDER BY count DESC"
    )
    return {row["bookshelf"]: row["count"] for row in cursor}


def get_format_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return book counts grouped by format, ordered by count descending.

    Books with an empty format string are excluded.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    dict of str to int
        Mapping of format name to book count.
    """
    cursor = conn.execute(
        "SELECT format, COUNT(*) as count FROM books WHERE format != '' GROUP BY format ORDER BY count DESC"
    )
    return {row["format"]: row["count"] for row in cursor}


def get_all_shelves(conn: sqlite3.Connection) -> list[str]:
    """Return all unique shelf names, sorted alphabetically.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    list of str
        Sorted shelf names.
    """
    cursor = conn.execute("SELECT DISTINCT bookshelf FROM books ORDER BY bookshelf")
    return [row["bookshelf"] for row in cursor]


def get_all_books_by_date(conn: sqlite3.Connection) -> list[Book]:
    """Return all books ordered by date added, most recent first.

    Books without a date are sorted to the end, then alphabetically by
    title.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    list of Book
        All books in date-descending order.
    """
    cursor = conn.execute(
        "SELECT * FROM books ORDER BY date_added IS NULL, date_added DESC, title"
    )
    return [_row_to_book(row) for row in cursor]


def get_last_added_date(conn: sqlite3.Connection) -> Optional[date]:
    """Return the date of the most recently added book.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.

    Returns
    -------
    date or None
        The most recent ``date_added`` value, or ``None`` if the database
        is empty or no books have a date.
    """
    cursor = conn.execute(
        "SELECT date_added FROM books WHERE date_added IS NOT NULL ORDER BY date_added DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if row:
        return _parse_date(row[0])
    return None


def search_books(conn: sqlite3.Connection, query: str) -> Iterator[Book]:
    """Search books by title, author, or ISBN using a LIKE pattern.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    query : str
        The search term (matched as a substring).

    Yields
    ------
    Book
        Books whose title, authors, or ISBN contain *query*.
    """
    pattern = f"%{query}%"
    cursor = conn.execute(
        """
        SELECT * FROM books
        WHERE title LIKE ? OR authors LIKE ? OR isbn LIKE ?
        ORDER BY title
        """,
        (pattern, pattern, pattern),
    )
    for row in cursor:
        yield _row_to_book(row)


# Allowed fields for update_book_fields
_UPDATABLE_FIELDS = {
    "book_id",
    "isbn",
    "title",
    "subtitle",
    "bookshelf",
    "date_added",
    "wishlist",
    "read",
    "pages_read",
    "number_of_copies",
    "signed",
    "authors",
    "language",
    "published_at",
    "publisher",
    "page_count",
    "description",
    "categories",
    "format",
    "series",
    "volume",
    "editors",
    "translators",
    "illustrators",
    "verified",
    "last_verified",
}

_BOOL_FIELDS = {"wishlist", "read", "signed", "verified"}
_DATE_FIELDS = {"date_added", "published_at", "last_verified"}


def update_book_fields(
    conn: sqlite3.Connection, isbn: str, updates: dict[str, any]
) -> bool:
    """Update specific fields for a book identified by ISBN.

    Date values are serialised to ISO format and boolean values are
    converted to integers before storage. The transaction is committed
    automatically on success.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    isbn : str
        ISBN of the book to update.
    updates : dict of str to any
        Mapping of field names to new values.

    Returns
    -------
    bool
        ``True`` if a row was updated, ``False`` if no matching book was
        found or *updates* was empty.

    Raises
    ------
    ValueError
        If *updates* contains a field name not in ``_UPDATABLE_FIELDS``.
    """
    # Validate field names
    invalid_fields = set(updates.keys()) - _UPDATABLE_FIELDS
    if invalid_fields:
        raise ValueError(f"Invalid field(s): {', '.join(invalid_fields)}")

    if not updates:
        return False

    # Build the SET clause
    set_parts = []
    values = []
    for field, value in updates.items():
        set_parts.append(f"{field} = ?")
        # Handle date serialization
        if field in _DATE_FIELDS and value is not None:
            if hasattr(value, "isoformat"):
                value = value.isoformat()
        elif field in _BOOL_FIELDS:
            value = int(value)
        values.append(value)

    values.append(isbn)
    query = f"UPDATE books SET {', '.join(set_parts)} WHERE isbn = ?"

    cursor = conn.execute(query, values)
    conn.commit()
    return cursor.rowcount > 0
