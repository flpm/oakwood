"""MCP server exposing Oakwood book catalogue as tools for LLM agents.

Provides read and write tools for searching, browsing, adding, updating,
verifying, and importing books. Requires the ``mcp`` optional dependency
(install with ``pip install oakwood[mcp]``).
"""

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit(
        "The 'mcp' package is required for the MCP server.\n"
        "Install it with: pip install oakwood[mcp]"
    )

import dataclasses
from datetime import date
from pathlib import Path
from typing import Optional

from .database import (
    book_exists,
    get_all_books,
    get_all_books_by_date,
    get_all_shelves,
    get_book_by_isbn,
    get_book_count,
    get_connection,
    get_format_counts,
    get_last_added_date,
    get_shelf_counts,
    init_db,
    insert_book,
    search_books,
    update_book_fields,
)
from .importer import import_csv
from .models import Book
from .openlibrary import OpenLibraryError, fetch_book
from .settings import load_settings

mcp = FastMCP("oakwood")

_settings = load_settings()
_conn = get_connection(_settings.resolve_db_path())
init_db(_conn)


def _book_to_dict(book: Book) -> dict:
    """Convert a Book dataclass to a JSON-serialisable dictionary.

    Parameters
    ----------
    book : Book
        The book to convert.

    Returns
    -------
    dict
        Book fields with ``date`` values converted to ISO strings.
    """
    d = dataclasses.asdict(book)
    for key, value in d.items():
        if isinstance(value, date):
            d[key] = value.isoformat()
    return d


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO-format date string.

    Parameters
    ----------
    value : str or None
        A date string in ``YYYY-MM-DD`` format, or ``None``.

    Returns
    -------
    date or None
        The parsed date, or ``None`` if the input is empty or invalid.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# --- Read tools ---


@mcp.tool()
def search_books_tool(query: str) -> list[dict]:
    """Search books by title, author, or ISBN.

    Parameters
    ----------
    query : str
        The search term (matched as a substring).

    Returns
    -------
    list of dict
        Matching books as dictionaries.
    """
    return [_book_to_dict(b) for b in search_books(_conn, query)]


@mcp.tool()
def get_book(isbn: str) -> dict | str:
    """Get a single book by ISBN.

    Parameters
    ----------
    isbn : str
        The ISBN to look up.

    Returns
    -------
    dict or str
        The book as a dictionary, or an error message if not found.
    """
    book = get_book_by_isbn(_conn, isbn)
    if book:
        return _book_to_dict(book)
    return f"No book found with ISBN: {isbn}"


@mcp.tool()
def list_books(shelf: str = "") -> list[dict]:
    """List all books, optionally filtered by shelf.

    Parameters
    ----------
    shelf : str
        If provided, only return books on this shelf.

    Returns
    -------
    list of dict
        Books sorted alphabetically by title.
    """
    return [_book_to_dict(b) for b in get_all_books(_conn, shelf or None)]


@mcp.tool()
def list_recent_books(limit: int = 20) -> list[dict]:
    """List the most recently added books.

    Parameters
    ----------
    limit : int
        Maximum number of books to return.

    Returns
    -------
    list of dict
        Books sorted by date added, most recent first.
    """
    books = get_all_books_by_date(_conn)
    return [_book_to_dict(b) for b in books[:limit]]


@mcp.tool()
def list_shelves() -> list[str]:
    """List all shelf names in the catalogue.

    Returns
    -------
    list of str
        Sorted shelf names.
    """
    return get_all_shelves(_conn)


@mcp.tool()
def get_catalogue_stats() -> dict:
    """Get summary statistics about the catalogue.

    Returns
    -------
    dict
        Statistics including book count, shelf counts, format counts,
        shelf names, and last added date.
    """
    last_added = get_last_added_date(_conn)
    return {
        "book_count": get_book_count(_conn),
        "shelf_counts": get_shelf_counts(_conn),
        "format_counts": get_format_counts(_conn),
        "shelves": get_all_shelves(_conn),
        "last_added": last_added.isoformat() if last_added else None,
    }


# --- Write tools ---


@mcp.tool()
def add_book(
    isbn: str,
    title: str,
    bookshelf: str,
    book_id: str = "",
    authors: str = "",
    publisher: str = "",
    published_at: str = "",
    page_count: int = 0,
    description: str = "",
    categories: str = "",
    format: str = "",
    subtitle: str = "",
    series: str = "",
    volume: str = "",
    language: str = "",
    date_added: str = "",
    editors: str = "",
    translators: str = "",
    illustrators: str = "",
    wishlist: bool = False,
    read: bool = False,
    signed: bool = False,
    pages_read: int = 0,
    number_of_copies: int = 1,
) -> dict | str:
    """Add a new book to the catalogue.

    Parameters
    ----------
    isbn : str
        ISBN (must be unique).
    title : str
        Book title.
    bookshelf : str
        Shelf name.
    book_id : str
        Unique book identifier. Defaults to ISBN if not provided.
    authors : str
        Comma-separated author names.
    publisher : str
        Publisher name.
    published_at : str
        Publication date as ISO string (YYYY-MM-DD).
    page_count : int
        Total pages.
    description : str
        Book description.
    categories : str
        Comma-separated categories.
    format : str
        Physical format (e.g. Hardcover, Paperback).
    subtitle : str
        Book subtitle.
    series : str
        Series name.
    volume : str
        Volume number.
    language : str
        Book language.
    date_added : str
        Date added as ISO string (YYYY-MM-DD). Defaults to today.
    editors : str
        Comma-separated editor names.
    translators : str
        Comma-separated translator names.
    illustrators : str
        Comma-separated illustrator names.
    wishlist : bool
        Whether the book is on the wishlist.
    read : bool
        Whether the book has been read.
    signed : bool
        Whether the copy is signed.
    pages_read : int
        Pages read so far.
    number_of_copies : int
        Number of copies owned.

    Returns
    -------
    dict or str
        The added book as a dictionary, or an error message.
    """
    if book_exists(_conn, isbn):
        return f"Book with ISBN {isbn} already exists"

    book = Book(
        book_id=book_id or isbn,
        isbn=isbn,
        title=title,
        bookshelf=bookshelf,
        authors=authors,
        publisher=publisher,
        published_at=_parse_iso_date(published_at),
        page_count=page_count,
        description=description,
        categories=categories,
        format=format,
        subtitle=subtitle,
        series=series,
        volume=volume,
        language=language,
        date_added=_parse_iso_date(date_added) or date.today(),
        editors=editors,
        translators=translators,
        illustrators=illustrators,
        wishlist=wishlist,
        read=read,
        signed=signed,
        pages_read=pages_read,
        number_of_copies=number_of_copies,
    )
    insert_book(_conn, book)
    _conn.commit()
    return _book_to_dict(book)


@mcp.tool()
def update_book(isbn: str, updates: dict) -> dict | str:
    """Update fields on an existing book.

    Parameters
    ----------
    isbn : str
        ISBN of the book to update.
    updates : dict
        Mapping of field names to new values. Date fields should be
        ISO strings (YYYY-MM-DD).

    Returns
    -------
    dict or str
        The updated book as a dictionary, or an error message.
    """
    # Convert ISO date strings to date objects
    date_fields = {"date_added", "published_at", "last_verified"}
    converted = {}
    for key, value in updates.items():
        if key in date_fields and isinstance(value, str):
            converted[key] = _parse_iso_date(value)
        else:
            converted[key] = value

    try:
        updated = update_book_fields(_conn, isbn, converted)
    except ValueError as e:
        return str(e)

    if not updated:
        return f"No book found with ISBN: {isbn}"

    book = get_book_by_isbn(_conn, isbn)
    return _book_to_dict(book) if book else "Book updated but could not be re-read"


@mcp.tool()
def verify_book(isbn: str, accept_api_values: bool = False) -> dict | str:
    """Verify a book against the Open Library API.

    Compares local data with Open Library and optionally applies API
    values for differing fields.

    Parameters
    ----------
    isbn : str
        ISBN of the book to verify.
    accept_api_values : bool
        If ``True``, automatically update local fields with API values
        where they differ.

    Returns
    -------
    dict or str
        A diff dictionary showing local vs API values for each compared
        field, or an error message.
    """
    book = get_book_by_isbn(_conn, isbn)
    if not book:
        return f"No book found with ISBN: {isbn}"

    try:
        api_book = fetch_book(isbn)
    except OpenLibraryError as e:
        return f"Open Library error: {e}"

    # Compare fields
    compare_fields = [
        ("title", book.title, api_book.title),
        ("authors", book.authors, api_book.authors),
        ("page_count", book.page_count, api_book.page_count),
        ("publisher", book.publisher, api_book.publisher),
        ("published_at", book.published_at, api_book.published_at),
        ("categories", book.categories, api_book.categories),
        ("description", book.description, api_book.description),
    ]

    diff = {}
    api_updates = {}
    for field_name, local_val, api_val in compare_fields:
        if api_val is None:
            continue
        # Normalise for comparison
        local_str = str(local_val) if local_val else ""
        api_str = str(api_val) if api_val else ""
        if local_str != api_str:
            diff[field_name] = {"local": local_str, "api": api_str}
            api_updates[field_name] = api_val

    if accept_api_values and api_updates:
        update_book_fields(_conn, isbn, api_updates)

    # Mark as verified
    update_book_fields(
        _conn, isbn, {"verified": True, "last_verified": date.today()}
    )

    return {
        "isbn": isbn,
        "differences": diff,
        "fields_updated": list(api_updates.keys()) if accept_api_values else [],
        "verified": True,
    }


@mcp.tool()
def import_csv_file(csv_path: str) -> dict | str:
    """Import books from a Bookshelf CSV export file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.

    Returns
    -------
    dict or str
        Counts of added and skipped books, or an error message.
    """
    path = Path(csv_path).expanduser()
    if not path.exists():
        return f"File not found: {csv_path}"

    try:
        added, skipped = import_csv(path, _conn)
    except Exception as e:
        return f"Import error: {e}"

    return {"added": added, "skipped": skipped}


def main() -> None:
    """Entry point for the ``oakwood-mcp`` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
