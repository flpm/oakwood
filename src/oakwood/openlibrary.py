"""Open Library API client for book verification.

Fetches book metadata from the Open Library Books API and returns it as
an ``OpenLibraryBook`` dataclass for comparison with local catalogue data.
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import date
from typing import Optional


class OpenLibraryError(Exception):
    """Raised when an Open Library API request fails or returns no data."""

    pass


@dataclass
class OpenLibraryBook:
    """Book metadata retrieved from the Open Library API.

    Only the fields used for verification are included. All fields
    default to ``None`` so that missing data can be distinguished from
    empty values.

    Attributes
    ----------
    title : str or None
        Book title.
    authors : str or None
        Comma-separated author names.
    page_count : int or None
        Number of pages.
    publisher : str or None
        First listed publisher name.
    published_at : date or None
        Publication date.
    categories : str or None
        Comma-separated subject names.
    description : str or None
        Book description (from excerpts).
    """

    title: Optional[str] = None
    authors: Optional[str] = None
    page_count: Optional[int] = None
    publisher: Optional[str] = None
    published_at: Optional[date] = None
    categories: Optional[str] = None
    description: Optional[str] = None


def _parse_publish_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a publish date string from Open Library.

    Handles several formats returned by the API.

    Parameters
    ----------
    date_str : str or None
        Raw date string from the API response.

    Returns
    -------
    date or None
        Parsed date, or ``None`` if the string is empty or unparseable.

    Examples
    --------
    >>> _parse_publish_date("2005")
    datetime.date(2005, 1, 1)
    >>> _parse_publish_date("March 2005")
    datetime.date(2005, 3, 1)
    >>> _parse_publish_date("March 21, 2005")
    datetime.date(2005, 3, 21)
    >>> _parse_publish_date("2005-03-21")
    datetime.date(2005, 3, 21)
    """
    if not date_str:
        return None

    # Try ISO format first
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        pass

    # Try year only
    if date_str.isdigit() and len(date_str) == 4:
        return date(int(date_str), 1, 1)

    # Try parsing month year or full date
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    parts = date_str.lower().replace(",", "").split()
    if len(parts) >= 2:
        # Try "Month Year" or "Month Day, Year"
        month_name = parts[0]
        if month_name in months:
            month = months[month_name]
            try:
                if len(parts) == 2:
                    # "March 2005"
                    year = int(parts[1])
                    return date(year, month, 1)
                elif len(parts) == 3:
                    # "March 21, 2005" or "March 21 2005"
                    day = int(parts[1])
                    year = int(parts[2])
                    return date(year, month, day)
            except (ValueError, TypeError):
                pass

    return None


def fetch_book(isbn: str) -> OpenLibraryBook:
    """Fetch book metadata from the Open Library Books API.

    Parameters
    ----------
    isbn : str
        The ISBN to look up.

    Returns
    -------
    OpenLibraryBook
        Parsed book metadata.

    Raises
    ------
    OpenLibraryError
        If the HTTP request fails, the response is malformed, or the
        ISBN is not found.
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise OpenLibraryError(f"Failed to connect to Open Library: {e}")
    except json.JSONDecodeError as e:
        raise OpenLibraryError(f"Invalid response from Open Library: {e}")

    key = f"ISBN:{isbn}"
    if key not in data:
        raise OpenLibraryError("Book not found in Open Library")

    book_data = data[key]

    # Parse authors
    authors = None
    if "authors" in book_data:
        author_names = [a.get("name", "") for a in book_data["authors"] if a.get("name")]
        if author_names:
            authors = ", ".join(author_names)

    # Parse publisher (first one)
    publisher = None
    if "publishers" in book_data:
        publishers = [p.get("name", "") for p in book_data["publishers"] if p.get("name")]
        if publishers:
            publisher = publishers[0]

    # Parse categories/subjects
    categories = None
    if "subjects" in book_data:
        subject_names = [s.get("name", "") for s in book_data["subjects"] if s.get("name")]
        if subject_names:
            categories = ", ".join(subject_names)

    # Parse description (from excerpts)
    description = None
    if "excerpts" in book_data:
        excerpts = [e.get("text", "") for e in book_data["excerpts"] if e.get("text")]
        if excerpts:
            description = excerpts[0]

    return OpenLibraryBook(
        title=book_data.get("title"),
        authors=authors,
        page_count=book_data.get("number_of_pages"),
        publisher=publisher,
        published_at=_parse_publish_date(book_data.get("publish_date")),
        categories=categories,
        description=description,
    )
