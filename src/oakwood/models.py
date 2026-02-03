"""Book data model for Oakwood catalogue.

Defines the ``Book`` dataclass used throughout the application to represent
a single book in the catalogue.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Book:
    """A book in the catalogue.

    Fields are grouped by expected population rate from CSV imports.

    Attributes
    ----------
    book_id : str
        Unique identifier from the source system.
    isbn : str
        ISBN used as the primary key for deduplication.
    title : str
        Main title of the book.
    bookshelf : str
        Name of the shelf the book belongs to.
    date_added : date or None
        Date the book was added to the catalogue.
    wishlist : bool
        Whether the book is on the wishlist.
    read : bool
        Whether the book has been read.
    pages_read : int
        Number of pages read so far.
    number_of_copies : int
        Number of copies owned.
    signed : bool
        Whether the copy is signed.
    authors : str
        Comma-separated author names.
    language : str
        Language of the book.
    published_at : date or None
        Publication date.
    publisher : str
        Publisher name.
    page_count : int
        Total number of pages.
    description : str
        Book description or synopsis.
    categories : str
        Comma-separated category/subject names.
    format : str
        Physical format (e.g. Hardcover, Paperback).
    subtitle : str
        Book subtitle.
    series : str
        Series name, if part of a series.
    volume : str
        Volume number within the series.
    editors : str
        Comma-separated editor names.
    translators : str
        Comma-separated translator names.
    illustrators : str
        Comma-separated illustrator names.
    verified : bool
        Whether the book data has been verified against Open Library.
    last_verified : date or None
        Date of the most recent verification.
    """

    # Core fields (100% populated)
    book_id: str
    isbn: str
    title: str
    bookshelf: str
    date_added: Optional[date] = None
    wishlist: bool = False
    read: bool = False
    pages_read: int = 0
    number_of_copies: int = 1
    signed: bool = False

    # Metadata (90%+ populated)
    authors: str = ""
    language: str = ""
    published_at: Optional[date] = None
    publisher: str = ""
    page_count: int = 0
    description: str = ""
    categories: str = ""
    format: str = ""

    # Series info (10-50% populated)
    subtitle: str = ""
    series: str = ""
    volume: str = ""

    # Contributors (<10% populated)
    editors: str = ""
    translators: str = ""
    illustrators: str = ""

    # Verification status
    verified: bool = False
    last_verified: Optional[date] = None

    def display_title(self, max_length: int = 50) -> str:
        """Return title truncated with ellipsis if needed.

        Parameters
        ----------
        max_length : int, optional
            Maximum character length before truncation, by default 50.

        Returns
        -------
        str
            The title, truncated with ``...`` if it exceeds *max_length*.
        """
        if len(self.title) <= max_length:
            return self.title
        return self.title[: max_length - 3] + "..."

    def display_authors(self, max_length: int = 30) -> str:
        """Return authors truncated with ellipsis if needed.

        Parameters
        ----------
        max_length : int, optional
            Maximum character length before truncation, by default 30.

        Returns
        -------
        str
            The authors string, truncated with ``...`` if it exceeds
            *max_length*.
        """
        if len(self.authors) <= max_length:
            return self.authors
        return self.authors[: max_length - 3] + "..."

    @property
    def full_title(self) -> str:
        """Return title with subtitle appended if present.

        Returns
        -------
        str
            ``"Title: Subtitle"`` when a subtitle exists, otherwise just the
            title.
        """
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title
