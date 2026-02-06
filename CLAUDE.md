# Oakwood Book Catalogue

A full-screen TUI for managing a personal book catalogue with support for importing books from Bookshelf iOS app CSV exports. Built with Textual. Includes an MCP server for LLM agent access.

## Project Structure

```
src/oakwood/
├── app.py                  # Textual App subclass, entry point, DB lifecycle
├── oakwood.tcss            # Warm dark theme (amber/gold on dark brown)
├── database.py             # SQLite operations (CRUD, search, stats)
├── models.py               # Book dataclass (26 fields)
├── settings.py             # Settings dataclass, load/save JSON from ~/.oakwood/
├── importer.py             # Bookshelf CSV import logic
├── backup.py               # Backup/restore logic (tar.gz archives)
├── openlibrary.py          # Open Library API client for verification
├── activity_log.py         # Centralized activity logging (JSON Lines)
├── mcp_server.py           # MCP server exposing catalogue as tools
├── screens/
│   ├── main.py             # Stats + search + DataTable of recent books
│   ├── book_detail.py      # Full book info panel + navigation
│   ├── book_edit.py        # Form for editing book fields
│   ├── verify.py           # Multi-phase API verification flow
│   ├── import_csv.py       # CSV import with progress log
│   ├── backup.py           # Backup table + create/restore actions
│   ├── activity.py         # Activity log browser with filters
│   └── about.py            # Version and credits
└── widgets/
    ├── stats_panel.py      # "N books | M shelves" bar + MCP indicator
    └── book_table.py       # DataTable wrapper with ISBN tracking
```

## Data Files

All user data is stored in `~/.oakwood/`:

```
~/.oakwood/
├── oakwood-settings.json   # Configuration
└── data/
    ├── oakwood.db          # SQLite database
    ├── activity.log        # Activity log (JSON Lines)
    └── backups/            # Backup archives
```

## Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode (with MCP server)
pip install -e ".[mcp]"

# Run TUI
oakwood

# Run MCP server (for testing)
oakwood-mcp
```

## Architecture

### TUI (Textual)

The app uses Textual's screen stack pattern:
- `OakwoodApp` in `app.py` manages DB connection and screen lifecycle
- Screens are pushed/popped via `self.app.push_screen()` / `self.app.pop_screen()`
- Each screen defines `BINDINGS` list and `compose()` method
- Background work uses `@work(thread=True)` decorator with `call_from_thread()` for UI updates

### MCP Server

Separate process (`oakwood-mcp`) that exposes the catalogue via MCP tools:
- 6 read tools: `search_books_tool`, `get_book`, `list_books`, `list_recent_books`, `list_shelves`, `get_catalogue_stats`
- 4 write tools: `add_book`, `update_book`, `verify_book`, `import_csv_file`
- Configured in `.mcp.json` at project root

### MCP Mode

TUI has an "MCP mode" (`m` key) that disables write operations to prevent conflicts when both TUI and MCP are active. Guards exist on import, edit, verify, and restore actions.

### Activity Logging

All data modifications are logged to `~/.oakwood/data/activity.log`:
- JSON Lines format (one JSON object per line)
- Uses `fcntl.flock()` for concurrent TUI + MCP safety
- Actions: `create`, `edit`, `import`, `backup`, `restore`, `verify`
- Sources: `tui` or `mcp`

## Screens

| Screen | Key | Description |
|--------|-----|-------------|
| MainScreen | (default) | Stats bar, search, book table. Keys: `/` search, `i` import, `b` backup, `a` activity, `m` MCP mode, `?` about, `q` quit |
| BookDetailScreen | Enter | Full book info. Keys: `e` edit, `v` verify, `←`/`→` prev/next book |
| BookEditScreen | `e` | Form with all editable fields. Keys: `Ctrl+S` save, `Esc` cancel |
| VerifyScreen | `v` | API verification. Keys: `1` keep local, `2` use API, `s` skip |
| ImportScreen | `i` | CSV file import with progress log |
| BackupScreen | `b` | Backup list + create/restore. Keys: `b` backup, `r` restore (double-press) |
| ActivityScreen | `a` | Activity log with action/source filters |
| AboutScreen | `?` | Version info |

## Dependencies

- **textual** - Full-screen TUI framework
- **pandas** - CSV parsing
- **mcp** (optional) - MCP server support

## Database

SQLite at `~/.oakwood/data/oakwood.db`. Key tables:
- `books` - All book data (ISBN is unique key)

Connection uses `check_same_thread=False` for Textual worker thread compatibility.

## Settings

Configuration in `~/.oakwood/oakwood-settings.json`:

```json
{
  "db_path": "data/oakwood.db",
  "covers_path": ""
}
```

Relative paths resolve from `~/.oakwood/`. Absolute paths and `~` expansion supported.

## Documentation

All Python code uses **numpydoc**-style docstrings:

- **Module docstrings** — one-line summary, optionally extended description
- **Class docstrings** — one-line summary, optional extended description, `Attributes` section
- **Function docstrings** — one-line summary, then: `Parameters`, `Returns`, `Raises`, `Notes`, `Examples`
- Simple one-line docstrings for trivial methods (`action_go_back`, etc.)

### Example

```python
def get_book_by_isbn(conn: sqlite3.Connection, isbn: str) -> Optional[Book]:
    """Look up a single book by ISBN.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    isbn : str
        The ISBN to look up.

    Returns
    -------
    Book or None
        The matching book, or ``None`` if not found.
    """
```

### Rules

- Use prose-friendly types: `str or None` not `Optional[str]`, `list of str` not `list[str]`
- Use double backticks for code: `` ``None`` ``, `` ``Book`` ``
- Keep descriptions concise (1-2 sentences per parameter)
