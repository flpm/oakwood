"""Textual TUI application for Oakwood book catalogue."""

from textual.app import App

from .database import get_connection, init_db
from .settings import load_settings


class OakwoodApp(App):
    """Oakwood Book Catalogue TUI."""

    TITLE = "Oakwood"
    SUB_TITLE = "Book Catalogue"
    CSS_PATH = "oakwood.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Create DB connection and initialize schema on mount."""
        self._settings = load_settings()
        self.db = get_connection(self._settings.resolve_db_path())
        init_db(self.db)
        from .screens.main import MainScreen
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        """Close DB connection on unmount."""
        if hasattr(self, "db"):
            self.db.close()


def main() -> None:
    """Entry point for the oakwood command."""
    app = OakwoodApp()
    app.run()


if __name__ == "__main__":
    main()
