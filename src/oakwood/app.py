"""Textual TUI application for Oakwood book catalogue.

Defines the ``OakwoodApp`` class (the Textual ``App`` subclass) and the
``main`` entry point used by the ``oakwood`` console script.
"""

from textual.app import App

from .database import get_connection, init_db
from .settings import load_settings


class OakwoodApp(App):
    """Oakwood Book Catalogue TUI.

    Manages the database connection lifecycle and pushes the initial
    ``MainScreen`` on mount.

    Attributes
    ----------
    db : sqlite3.Connection
        Shared database connection, available after mount.
    """

    TITLE = "Oakwood"
    SUB_TITLE = "Book Catalogue"
    CSS_PATH = "oakwood.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Load settings, open the database, and push the main screen."""
        self._settings = load_settings()
        self.db = get_connection(self._settings.resolve_db_path())
        init_db(self.db)
        from .screens.main import MainScreen
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        """Close the database connection when the app exits."""
        if hasattr(self, "db"):
            self.db.close()


def main() -> None:
    """Entry point for the ``oakwood`` console script."""
    app = OakwoodApp()
    app.run()


if __name__ == "__main__":
    main()
