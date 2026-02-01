"""Stats panel widget displaying collection summary."""

from textual.widgets import Static


class StatsPanel(Static):
    """Displays book count and shelf count summary."""

    def update_stats(self, book_count: int, shelf_count: int) -> None:
        """Update the stats display."""
        self.update(f"{book_count} books  |  {shelf_count} shelves")
