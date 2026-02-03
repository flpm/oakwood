"""Import screen for importing books from CSV files.

Provides a file path input, an import button, and a scrollable log that
shows per-book progress and a final summary.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Input, RichLog, Static
from textual import work

from ..importer import import_csv


class ImportScreen(Screen):
    """CSV import screen with file path input, progress log, and summary."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Build the import screen layout."""
        with Vertical(id="import-container"):
            yield Static("[bold]Import Books from CSV[/bold]", id="import-title")
            with Horizontal(id="import-path-row"):
                yield Input(placeholder="Path to CSV file...", id="import-path-input")
                yield Button("Import", id="import-button")
            yield RichLog(highlight=True, markup=True, id="import-log")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Start the import when the Import button is pressed."""
        if event.button.id == "import-button":
            self._start_import()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Start the import when Enter is pressed in the path input."""
        if event.input.id == "import-path-input":
            self._start_import()

    def _start_import(self) -> None:
        """Validate the file path and launch the background import worker."""
        path_str = self.query_one("#import-path-input", Input).value.strip()
        if not path_str:
            self._log("[#c45a3a]Please enter a CSV file path.[/#c45a3a]")
            return

        path = Path(path_str).expanduser()
        if not path.exists():
            self._log(f"[#c45a3a]File not found: {path}[/#c45a3a]")
            return

        self.query_one("#import-button", Button).disabled = True
        self.query_one("#import-path-input", Input).disabled = True
        self._log(f"[#8a7e6a]Importing from {path.name}...[/#8a7e6a]")
        self._run_import(path)

    def _log(self, message: str) -> None:
        """Append a Rich markup message to the import log.

        Parameters
        ----------
        message : str
            Rich markup text to display.
        """
        self.query_one("#import-log", RichLog).write(message)

    @work(exclusive=True, thread=True)
    def _run_import(self, path: Path) -> None:
        """Run the CSV import in a background thread.

        Parameters
        ----------
        path : Path
            Validated path to the CSV file.
        """
        conn = self.app.db

        def on_book(book, is_new):
            if is_new:
                self.app.call_from_thread(
                    self._log,
                    f"[#6a9a4a]+[/#6a9a4a] {book.display_title(60)}",
                )
            else:
                self.app.call_from_thread(
                    self._log,
                    f"[#8a7e6a]=[/#8a7e6a] {book.display_title(60)} [#8a7e6a](skipped)[/#8a7e6a]",
                )

        try:
            added, skipped = import_csv(path, conn, on_book=on_book)
            self.app.call_from_thread(self._show_summary, added, skipped)
        except Exception as e:
            self.app.call_from_thread(
                self._log, f"[#c45a3a]Error: {e}[/#c45a3a]"
            )
            self.app.call_from_thread(self._re_enable_input)

    def _show_summary(self, added: int, skipped: int) -> None:
        """Log the import summary and re-enable the input controls.

        Parameters
        ----------
        added : int
            Number of books added.
        skipped : int
            Number of books skipped.
        """
        self._log("")
        if skipped > 0:
            self._log(f"[bold]Imported {added} books ({skipped} skipped)[/bold]")
        else:
            self._log(f"[bold]Imported {added} books[/bold]")
        self._re_enable_input()

    def _re_enable_input(self) -> None:
        """Re-enable the path input and import button after an import."""
        self.query_one("#import-button", Button).disabled = False
        self.query_one("#import-path-input", Input).disabled = False

    def action_go_back(self) -> None:
        """Pop this screen and return to the main screen."""
        self.app.pop_screen()
