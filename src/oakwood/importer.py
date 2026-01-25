"""Bookshelf CSV import logic for Oakwood catalogue."""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from .database import book_exists, insert_book
from .models import Book


def _parse_date(date_str: str) -> Optional[date]:
    """Parse a date string from CSV."""
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
    """Parse an integer value from CSV."""
    if pd.isna(value):
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _parse_bool(value) -> bool:
    """Parse a boolean value from CSV."""
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
    """Parse a string value from CSV."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _row_to_book(row: pd.Series) -> Book:
    """Convert a pandas row to a Book object."""
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

    Args:
        csv_path: Path to the CSV file
        conn: Database connection
        on_book: Optional callback called for each book with (book, is_new) args

    Returns:
        Tuple of (added_count, skipped_count)
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
