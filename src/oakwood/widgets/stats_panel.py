"""Stats panel widget displaying collection summary.

Shows the application version, database path, book count, shelf count,
and date of the most recently added book.
"""

from datetime import date
from typing import Optional

from textual.widgets import Static


class StatsPanel(Static):
    """Single-line stats bar at the top of the main screen."""

    def update_stats(
        self,
        version: str,
        db_path: str,
        book_count: int,
        shelf_count: int,
        last_added: Optional[date],
    ) -> None:
        """Refresh the stats bar content.

        Parameters
        ----------
        version : str
            Application version string (e.g. ``"0.1.0"``).
        db_path : str
            Display path of the database file.
        book_count : int
            Total number of books in the catalogue.
        shelf_count : int
            Number of distinct shelves.
        last_added : date or None
            Date of the most recently added book, or ``None``.
        """
        last = str(last_added) if last_added else "-"
        self.update(
            f"[bold]Oakwood {version}[/bold]  |  {db_path}  |  "
            f"{book_count} books, {shelf_count} shelves  |  "
            f"last added: {last}"
        )
