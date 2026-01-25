"""Open Library API client for book verification."""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import date
from typing import Optional


class OpenLibraryError(Exception):
    """Exception raised for Open Library API errors."""

    pass


@dataclass
class OpenLibraryBook:
    """Parsed book data from Open Library API."""

    title: Optional[str] = None
    authors: Optional[str] = None
    page_count: Optional[int] = None
    publisher: Optional[str] = None
    published_at: Optional[date] = None
    categories: Optional[str] = None
    description: Optional[str] = None


def _parse_publish_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a publish date string from Open Library.

    Handles various formats:
    - "2005" -> date(2005, 1, 1)
    - "March 2005" -> date(2005, 3, 1)
    - "March 21, 2005" -> date(2005, 3, 21)
    - "2005-03-21" -> date(2005, 3, 21)
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
    """Fetch book data from Open Library API.

    Args:
        isbn: The ISBN to look up

    Returns:
        OpenLibraryBook with parsed data

    Raises:
        OpenLibraryError: If the request fails or book is not found
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
