"""Stats panel widget displaying collection summary."""

from datetime import date
from typing import Optional

from textual.widgets import Static


class StatsPanel(Static):
    """Displays app name, DB location, book/shelf counts, and last added date."""

    def update_stats(
        self,
        version: str,
        db_path: str,
        book_count: int,
        shelf_count: int,
        last_added: Optional[date],
    ) -> None:
        """Update the stats display."""
        last = str(last_added) if last_added else "-"
        self.update(
            f"[bold]Oakwood {version}[/bold]  |  {db_path}  |  "
            f"{book_count} books, {shelf_count} shelves  |  "
            f"last added: {last}"
        )
