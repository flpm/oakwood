"""Bookshelf CSV import logic for Oakwood catalogue.

Reads CSV exports from the Bookshelf iOS app and inserts new books into
the database, skipping duplicates based on ISBN.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from .database import book_exists, insert_book
from .models import Book


def _parse_date(date_str: str) -> Optional[date]:
    """Parse a date string from a CSV cell.

    Parameters
    ----------
    date_str : str
        Raw date value from the CSV. May be ``NaN`` or empty.

    Returns
    -------
    date or None
        Parsed date in ISO format, or ``None`` if unparseable.
    """
    if pd.isna(date_str) or not date_str:
        return None
    try:
        # Handle various date formats
        if isinstance(date_str, str):
            # Try ISO format first (YYYY-MM-DD)
            return date.fromisoformat(date_str)
    except ValueError:
        pass
    return None


def _parse_int(value) -> int:
    """Parse an integer value from a CSV cell.

    Parameters
    ----------
    value : any
        Raw value from the CSV. May be ``NaN``.

    Returns
    -------
    int
        Parsed integer, or ``0`` if the value is missing or invalid.
    """
    if pd.isna(value):
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _parse_bool(value) -> bool:
    """Parse a boolean value from a CSV cell.

    Accepts ``1``, ``true``, ``yes`` (case-insensitive) as truthy.

    Parameters
    ----------
    value : any
        Raw value from the CSV. May be ``NaN``.

    Returns
    -------
    bool
        Parsed boolean, or ``False`` if the value is missing.
    """
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return False


def _parse_str(value) -> str:
    """Parse a string value from a CSV cell.

    Parameters
    ----------
    value : any
        Raw value from the CSV. May be ``NaN``.

    Returns
    -------
    str
        Stripped string, or ``""`` if the value is missing.
    """
    if pd.isna(value):
        return ""
    return str(value).strip()


def _row_to_book(row: pd.Series) -> Book:
    """Convert a pandas row to a Book instance.

    Maps Bookshelf CSV column names to ``Book`` dataclass fields.

    Parameters
    ----------
    row : pandas.Series
        A single row from the CSV DataFrame.

    Returns
    -------
    Book
        A populated ``Book`` instance.
    """
    return Book(
        book_id=_parse_str(row.get("Book Id", "")),
        isbn=_parse_str(row.get("ISBN", "")),
        title=_parse_str(row.get("Title", "")),
        bookshelf=_parse_str(row.get("Bookshelf", "")),
        date_added=_parse_date(row.get("Date added", "")),
        wishlist=_parse_bool(row.get("Wishlist", 0)),
        read=_parse_bool(row.get("Read", 0)),
        pages_read=_parse_int(row.get("Pages Read", 0)),
        number_of_copies=_parse_int(row.get("Number of copies", 1)) or 1,
        signed=_parse_bool(row.get("Signed", 0)),
        authors=_parse_str(row.get("Authors", "")),
        language=_parse_str(row.get("Language", "")),
        published_at=_parse_date(row.get("Published At", "")),
        publisher=_parse_str(row.get("Publisher", "")),
        page_count=_parse_int(row.get("Page Count", 0)),
        description=_parse_str(row.get("Description", "")),
        categories=_parse_str(row.get("Categories", "")),
        format=_parse_str(row.get("Format", "")),
        subtitle=_parse_str(row.get("Subtitle", "")),
        series=_parse_str(row.get("Series", "")),
        volume=_parse_str(row.get("Volume", "")),
        editors=_parse_str(row.get("Editors", "")),
        translators=_parse_str(row.get("Translators", "")),
        illustrators=_parse_str(row.get("Illustrators", "")),
    )


def import_csv(
    csv_path: Path,
    conn: sqlite3.Connection,
    on_book: Optional[Callable[[Book, bool], None]] = None,
) -> tuple[int, int]:
    """Import books from a Bookshelf CSV export.

    Books without an ISBN or whose ISBN already exists in the database are
    skipped. The transaction is committed after all rows are processed.

    Parameters
    ----------
    csv_path : Path
        Path to the CSV file.
    conn : sqlite3.Connection
        An open database connection.
    on_book : callable, optional
        Callback invoked for each row as ``on_book(book, is_new)`` where
        *is_new* is ``True`` when the book was inserted.

    Returns
    -------
    tuple of (int, int)
        ``(added_count, skipped_count)``.
    """
    df = pd.read_csv(csv_path)

    added = 0
    skipped = 0

    for _, row in df.iterrows():
        book = _row_to_book(row)

        # Skip books without ISBN
        if not book.isbn:
            skipped += 1
            if on_book:
                on_book(book, False)
            continue

        # Check for duplicates
        if book_exists(conn, book.isbn):
            skipped += 1
            if on_book:
                on_book(book, False)
            continue

        insert_book(conn, book)
        added += 1
        if on_book:
            on_book(book, True)

    conn.commit()
    return added, skipped
