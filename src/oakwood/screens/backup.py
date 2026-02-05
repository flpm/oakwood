"""Backup and restore screen for Oakwood catalogue.

Displays a table of existing backups and provides actions to create new
backups or restore from a selected backup. Uses background workers for
I/O-bound operations and ``call_from_thread`` for UI updates.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, RichLog, Static
from textual import work

from ..backup import (
    BackupInfo,
    create_backup,
    format_size,
    list_backups,
    restore_backup,
)
from ..database import get_connection, init_db


class BackupScreen(Screen):
    """Backup and restore screen with backup table and progress log.

    Attributes
    ----------
    _busy : bool
        Whether a backup or restore operation is in progress.
    _confirm_restore : bool
        Whether the first ``r`` press has been registered for
        double-press confirmation.
    _backup_map : dict
        Mapping of ``RowKey`` to ``BackupInfo`` for the current table.
    """

    BINDINGS = [
        Binding("b", "create_backup", "Backup"),
        Binding("r", "restore_backup", "Restore"),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        self._confirm_restore = False
        self._backup_map: dict = {}

    def compose(self) -> ComposeResult:
        """Build the backup screen layout."""
        with Vertical(id="backup-container"):
            yield Static("[bold]Backup & Restore[/bold]", id="backup-title")
            yield DataTable(id="backup-table", cursor_type="row")
            yield RichLog(highlight=True, markup=True, id="backup-log")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table columns and load existing backups."""
        table = self.query_one("#backup-table", DataTable)
        table.add_columns("Filename", "Size", "Created")
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Reload backups from disk into the table."""
        table = self.query_one("#backup-table", DataTable)
        table.clear()
        self._backup_map.clear()

        db_path = self.app._settings.resolve_db_path()
        backups = list_backups(db_path)

        for backup in backups:
            row_key = table.add_row(
                backup.filename,
                format_size(backup.size_bytes),
                backup.created.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._backup_map[row_key] = backup

    def _log(self, message: str) -> None:
        """Append a Rich markup message to the progress log.

        Parameters
        ----------
        message : str
            Rich markup text to display.
        """
        self.query_one("#backup-log", RichLog).write(message)

    def action_create_backup(self) -> None:
        """Create a new backup (bound to ``b``)."""
        if self._busy:
            self.notify("Operation in progress...", severity="warning")
            return
        self._confirm_restore = False
        self._busy = True
        self._run_backup()

    @work(exclusive=True, thread=True)
    def _run_backup(self) -> None:
        """Run the backup in a background thread."""
        db_path = self.app._settings.resolve_db_path()
        covers_path = self.app._settings.resolve_covers_path()

        def on_progress(msg):
            self.app.call_from_thread(self._log, f"[#8a7e6a]{msg}[/#8a7e6a]")

        try:
            # Flush WAL before archiving
            self.app.call_from_thread(self._flush_wal)

            info = create_backup(db_path, covers_path, on_progress=on_progress)
            self.app.call_from_thread(
                self._log,
                f"[#6a9a4a]Backup created: {info.filename} ({format_size(info.size_bytes)})[/#6a9a4a]",
            )
            self.app.call_from_thread(self._refresh_table)
        except Exception as e:
            self.app.call_from_thread(
                self._log, f"[#c45a3a]Backup failed: {e}[/#c45a3a]"
            )
        finally:
            self.app.call_from_thread(self._set_not_busy)

    def _flush_wal(self) -> None:
        """Flush the SQLite WAL to ensure a consistent backup."""
        try:
            self.app.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass

    def action_restore_backup(self) -> None:
        """Restore from the selected backup (bound to ``r``).

        Uses double-press confirmation: the first press shows a warning,
        the second press executes the restore.
        """
        if self._busy:
            self.notify("Operation in progress...", severity="warning")
            return

        if self.app.mcp_mode:
            self.notify("Restore disabled in MCP mode", severity="warning")
            return

        table = self.query_one("#backup-table", DataTable)
        if table.row_count == 0:
            self.notify("No backups available", severity="warning")
            return

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        backup = self._backup_map.get(row_key)
        if not backup:
            self.notify("Select a backup first", severity="warning")
            return

        if not self._confirm_restore:
            self._confirm_restore = True
            self._log(
                f"[#d4a04a]Press 'r' again to restore from {backup.filename}. "
                f"Current database will be saved as .pre-restore.[/#d4a04a]"
            )
            return

        # Second press — execute restore
        self._confirm_restore = False
        self._busy = True
        self._run_restore(backup)

    @work(exclusive=True, thread=True)
    def _run_restore(self, backup: BackupInfo) -> None:
        """Run the restore in a background thread.

        Parameters
        ----------
        backup : BackupInfo
            The backup to restore from.
        """
        db_path = self.app._settings.resolve_db_path()
        covers_path = self.app._settings.resolve_covers_path()

        def on_progress(msg):
            self.app.call_from_thread(self._log, f"[#8a7e6a]{msg}[/#8a7e6a]")

        try:
            # Close DB on main thread
            self.app.call_from_thread(self._close_db)

            restore_backup(backup.path, db_path, covers_path, on_progress=on_progress)

            # Reopen DB on main thread
            self.app.call_from_thread(self._reopen_db)

            self.app.call_from_thread(
                self._log,
                f"[#6a9a4a]Restored from {backup.filename}[/#6a9a4a]",
            )
            self.app.call_from_thread(self._refresh_table)
        except Exception as e:
            self.app.call_from_thread(
                self._log, f"[#c45a3a]Restore failed: {e}[/#c45a3a]"
            )
            # Try to reopen DB from whatever state exists
            self.app.call_from_thread(self._reopen_db)
        finally:
            self.app.call_from_thread(self._set_not_busy)

    def _close_db(self) -> None:
        """Close the application database connection."""
        try:
            self.app.db.close()
        except Exception:
            pass

    def _reopen_db(self) -> None:
        """Reopen the application database connection."""
        db_path = self.app._settings.resolve_db_path()
        self.app.db = get_connection(db_path)
        init_db(self.app.db)

    def _set_not_busy(self) -> None:
        """Clear the busy flag after an operation completes."""
        self._busy = False

    def on_key(self, event) -> None:
        """Reset restore confirmation when a non-r key is pressed."""
        if event.key != "r" and self._confirm_restore:
            self._confirm_restore = False

    def action_go_back(self) -> None:
        """Pop this screen and return to the main screen."""
        if self._busy:
            self.notify("Wait for operation to finish", severity="warning")
            return
        self.app.pop_screen()
