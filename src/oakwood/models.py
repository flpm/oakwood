"""Book data model for Oakwood catalogue."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Book:
    """Represents a book in the catalogue."""

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
        """Return title truncated with ellipsis if needed."""
        if len(self.title) <= max_length:
            return self.title
        return self.title[: max_length - 3] + "..."

    def display_authors(self, max_length: int = 30) -> str:
        """Return authors truncated with ellipsis if needed."""
        if len(self.authors) <= max_length:
            return self.authors
        return self.authors[: max_length - 3] + "..."

    @property
    def full_title(self) -> str:
        """Return title with subtitle if present."""
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title
