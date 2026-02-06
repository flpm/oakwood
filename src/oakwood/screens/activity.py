"""Activity log screen for browsing recent activity entries.

Displays a DataTable of recent activity log entries with filtering options
by action type and source.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Select, Static

from ..activity_log import ActivityEntry, read_recent_activity

_ACTION_CHOICES = [
    ("All actions", ""),
    ("Create", "create"),
    ("Edit", "edit"),
    ("Import", "import"),
    ("Backup", "backup"),
    ("Restore", "restore"),
    ("Verify", "verify"),
]

_SOURCE_CHOICES = [
    ("All sources", ""),
    ("TUI", "tui"),
    ("MCP", "mcp"),
]


class ActivityScreen(Screen):
    """Activity log browser with filters for action type and source.

    Attributes
    ----------
    _entries : list of ActivityEntry
        All loaded activity entries.
    _action_filter : str
        Current action filter (empty string = all).
    _source_filter : str
        Current source filter (empty string = all).
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ActivityEntry] = []
        self._action_filter = ""
        self._source_filter = ""

    def compose(self) -> ComposeResult:
        """Build the activity screen layout."""
        with Vertical(id="activity-container"):
            yield Static("[bold]Activity Log[/bold]", id="activity-title")
            with Horizontal(id="activity-filters"):
                yield Static("Action:", classes="filter-label")
                yield Select(
                    _ACTION_CHOICES,
                    value="",
                    id="activity-action-filter",
                    allow_blank=False,
                )
                yield Static("Source:", classes="filter-label")
                yield Select(
                    _SOURCE_CHOICES,
                    value="",
                    id="activity-source-filter",
                    allow_blank=False,
                )
            yield DataTable(id="activity-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table columns and load activity entries."""
        table = self.query_one("#activity-table", DataTable)
        table.add_columns("Time", "Action", "Source", "Title/ISBN", "Details")
        self._load_entries()

    def _load_entries(self) -> None:
        """Load activity entries from the log file."""
        self._entries = read_recent_activity(limit=200)
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table with filtered entries."""
        table = self.query_one("#activity-table", DataTable)
        table.clear()

        for entry in self._entries:
            # Apply filters
            if self._action_filter and entry.action != self._action_filter:
                continue
            if self._source_filter and entry.source != self._source_filter:
                continue

            # Format timestamp (show date and time without microseconds)
            ts = entry.timestamp
            if "." in ts:
                ts = ts.split(".")[0]
            if "T" in ts:
                ts = ts.replace("T", " ")

            # Format title/isbn
            identifier = entry.title or entry.isbn or "-"
            if len(identifier) > 35:
                identifier = identifier[:32] + "..."

            # Format details summary
            details = self._format_details(entry)

            table.add_row(
                ts,
                entry.action.capitalize(),
                entry.source.upper(),
                identifier,
                details,
            )

    def _format_details(self, entry: ActivityEntry) -> str:
        """Format the details dict for display.

        Parameters
        ----------
        entry : ActivityEntry
            The activity entry.

        Returns
        -------
        str
            A concise summary of the details.
        """
        d = entry.details
        if not d:
            return "-"

        parts = []
        if entry.action == "create":
            if "bookshelf" in d:
                parts.append(f"shelf: {d['bookshelf']}")
        elif entry.action == "edit":
            if "changed_fields" in d:
                fields = d["changed_fields"]
                if len(fields) <= 3:
                    parts.append(", ".join(fields))
                else:
                    parts.append(f"{len(fields)} fields")
        elif entry.action == "import":
            if "added_count" in d:
                parts.append(f"+{d['added_count']}")
            if "skipped_count" in d and d["skipped_count"] > 0:
                parts.append(f"skipped {d['skipped_count']}")
        elif entry.action == "backup":
            if "backup_filename" in d:
                parts.append(d["backup_filename"])
        elif entry.action == "restore":
            if "backup_filename" in d:
                parts.append(d["backup_filename"])
        elif entry.action == "verify":
            updated = d.get("fields_updated", [])
            skipped = d.get("fields_skipped", [])
            if updated:
                parts.append(f"updated: {len(updated)}")
            if skipped:
                parts.append(f"skipped: {len(skipped)}")

        result = ", ".join(parts) if parts else "-"
        if len(result) > 40:
            result = result[:37] + "..."
        return result

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter dropdown changes."""
        if event.select.id == "activity-action-filter":
            self._action_filter = event.value if event.value else ""
            self._refresh_table()
        elif event.select.id == "activity-source-filter":
            self._source_filter = event.value if event.value else ""
            self._refresh_table()

    def action_refresh(self) -> None:
        """Reload activity entries from disk (bound to ``r``)."""
        self._load_entries()
        self.notify("Activity log refreshed")

    def action_go_back(self) -> None:
        """Pop this screen and return to the main screen."""
        self.app.pop_screen()
