"""Verify screen for comparing book data against Open Library API.

Implements a multi-phase workflow: fetch API data, show a comparison
table, walk through differing fields one by one, and display a summary.
"""

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Footer, LoadingIndicator, Static
from textual import work

from ..activity_log import log_activity
from ..database import get_book_by_isbn, update_book_fields
from ..openlibrary import OpenLibraryError, fetch_book

VERIFIABLE_FIELDS = [
    "title",
    "authors",
    "page_count",
    "publisher",
    "published_at",
    "categories",
    "description",
]


class VerifyScreen(Screen):
    """Multi-phase verification screen.

    Phases
    ------
    1. Loading — fetching data from the Open Library API.
    2. Comparison table — showing fields that differ.
    3. Field resolution — user picks local value, API value, or skip for
       each differing field.
    4. Summary — applied updates and verification timestamp.

    Parameters
    ----------
    isbn : str
        ISBN of the book to verify.
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("1", "choose_local", "Keep Local", show=False),
        Binding("2", "choose_api", "Use API", show=False),
        Binding("s", "choose_skip", "Skip", show=False),
    ]

    phase = reactive(1)

    def __init__(self, isbn: str) -> None:
        super().__init__()
        self.isbn = isbn
        self._book = None
        self._api_book = None
        self._differences: list[tuple[str, str, str]] = []
        self._current_field_idx = 0
        self._updates: dict = {}
        self._updated_fields: list[str] = []
        self._skipped_fields: list[str] = []

    def compose(self) -> ComposeResult:
        """Build the screen layout with all phase widgets."""
        with VerticalScroll(id="verify-container"):
            yield Static("", id="verify-title")
            yield LoadingIndicator(id="verify-loading")
            yield Static("", id="verify-status")
            yield DataTable(id="verify-table")
            yield Static("", id="verify-field-prompt")
            yield Static("", id="verify-summary")
        yield Footer()

    def on_mount(self) -> None:
        """Load the local book and start the API fetch."""
        self._book = get_book_by_isbn(self.app.db, self.isbn)
        if not self._book:
            self.query_one("#verify-status").update(
                f"[#c45a3a]No book found with ISBN: {self.isbn}[/#c45a3a]"
            )
            self.query_one("#verify-loading").display = False
            return

        self.query_one("#verify-title").update(
            f"[bold]Verifying: {self._book.display_title(60)}[/bold]"
        )

        # Hide phase 2-4 widgets initially
        self.query_one("#verify-table").display = False
        self.query_one("#verify-field-prompt").display = False
        self.query_one("#verify-summary").display = False

        self._fetch_api_data()

    @work(exclusive=True, thread=True)
    def _fetch_api_data(self) -> None:
        """Fetch book metadata from Open Library in a background thread."""
        try:
            api_book = fetch_book(self.isbn)
            self.app.call_from_thread(self._on_api_data, api_book)
        except OpenLibraryError as e:
            self.app.call_from_thread(self._on_api_error, str(e))

    def _on_api_error(self, error: str) -> None:
        """Display an error message when the API request fails.

        Parameters
        ----------
        error : str
            Human-readable error description.
        """
        self.query_one("#verify-loading").display = False
        self.query_one("#verify-status").update(f"[#c45a3a]{error}[/#c45a3a]")

    def _on_api_data(self, api_book) -> None:
        """Compare local and API data, then advance to the appropriate phase.

        If all verifiable fields match, the book is automatically marked
        as verified. Otherwise the comparison table is shown.

        Parameters
        ----------
        api_book : OpenLibraryBook
            Metadata retrieved from the API.
        """
        self._api_book = api_book
        self.query_one("#verify-loading").display = False

        # Compare fields
        self._differences = []
        for field in VERIFIABLE_FIELDS:
            local_val = getattr(self._book, field)
            api_val = getattr(api_book, field)
            local_str = str(local_val) if local_val else ""
            api_str = str(api_val) if api_val else ""
            if api_val is not None and local_str != api_str:
                self._differences.append((field, local_str, api_str))

        if not self._differences:
            # No differences - auto-verify
            update_book_fields(
                self.app.db, self.isbn,
                {"verified": True, "last_verified": date.today()},
            )
            self.query_one("#verify-status").update(
                "[#6a9a4a]All verifiable fields match. Book marked as verified.[/#6a9a4a]"
            )
            return

        # Show comparison table (phase 2)
        self.phase = 2
        self._show_comparison_table()

    def _show_comparison_table(self) -> None:
        """Populate and display the side-by-side comparison table."""
        self.query_one("#verify-status").update(
            "[#8a7e6a]Differences found. Press Enter to resolve field by field.[/#8a7e6a]"
        )

        table = self.query_one("#verify-table", DataTable)
        table.display = True
        table.cursor_type = "row"
        table.add_columns("Field", "Local", "Open Library")
        for field, local_val, api_val in self._differences:
            display_field = field.replace("_", " ").title()
            table.add_row(
                display_field,
                local_val if local_val else "-",
                api_val if api_val else "-",
            )

        # Start field resolution (phase 3)
        self.phase = 3
        self._current_field_idx = 0
        self._show_field_prompt()

    def _show_field_prompt(self) -> None:
        """Display the prompt for the current differing field.

        Automatically advances to the summary phase when all fields have
        been resolved.
        """
        if self._current_field_idx >= len(self._differences):
            self._finish_verification()
            return

        field, local_val, api_val = self._differences[self._current_field_idx]
        display_field = field.replace("_", " ").title()

        prompt_text = (
            f"[bold][#d4a04a]{display_field}[/#d4a04a][/bold]\n"
            f"  [#8a7e6a]1.[/#8a7e6a] Keep local:  \"{local_val or '-'}\"\n"
            f"  [#8a7e6a]2.[/#8a7e6a] Use API:     \"{api_val or '-'}\"\n"
            f"  [#8a7e6a]s.[/#8a7e6a] Skip\n"
            f"\n[#8a7e6a]Field {self._current_field_idx + 1} of {len(self._differences)}[/#8a7e6a]"
        )
        self.query_one("#verify-field-prompt").update(prompt_text)
        self.query_one("#verify-field-prompt").display = True

    def action_choose_local(self) -> None:
        """Keep the local value for the current field (bound to ``1``)."""
        if self.phase != 3:
            return
        field, _, _ = self._differences[self._current_field_idx]
        self._skipped_fields.append(field.replace("_", " ").title())
        self._current_field_idx += 1
        self._show_field_prompt()

    def action_choose_api(self) -> None:
        """Accept the API value for the current field (bound to ``2``)."""
        if self.phase != 3:
            return
        field, _, _ = self._differences[self._current_field_idx]
        api_typed = getattr(self._api_book, field)
        self._updates[field] = api_typed
        self._updated_fields.append(field.replace("_", " ").title())
        self._current_field_idx += 1
        self._show_field_prompt()

    def action_choose_skip(self) -> None:
        """Skip the current field without changing it (bound to ``s``)."""
        if self.phase != 3:
            return
        field, _, _ = self._differences[self._current_field_idx]
        self._skipped_fields.append(field.replace("_", " ").title())
        self._current_field_idx += 1
        self._show_field_prompt()

    def _finish_verification(self) -> None:
        """Apply accumulated updates, mark verified, and show the summary."""
        self.phase = 4
        self.query_one("#verify-field-prompt").display = False
        self.query_one("#verify-table").display = False

        # Apply updates
        self._updates["verified"] = True
        self._updates["last_verified"] = date.today()
        update_book_fields(self.app.db, self.isbn, self._updates)

        # Log the verification
        log_activity(
            "verify", "tui",
            isbn=self.isbn,
            title=self._book.title,
            fields_updated=self._updated_fields,
            fields_skipped=self._skipped_fields,
        )

        # Show summary
        lines = ["[bold]Verification complete[/bold]", ""]
        if self._updated_fields:
            lines.append(f"[#6a9a4a]Updated:[/#6a9a4a] {', '.join(self._updated_fields)}")
        if self._skipped_fields:
            lines.append(f"[#8a7e6a]Skipped:[/#8a7e6a] {', '.join(self._skipped_fields)}")
        lines.append(f"\nMarked as verified on {date.today()}")

        self.query_one("#verify-status").update("")
        self.query_one("#verify-summary").update("\n".join(lines))
        self.query_one("#verify-summary").display = True

    def action_go_back(self) -> None:
        """Pop this screen and return to book detail."""
        self.app.pop_screen()
