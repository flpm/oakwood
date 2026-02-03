# Oakwood Book Catalogue

A full-screen TUI for managing a personal book catalogue with support for importing books from Bookshelf iOS app CSV exports. Built with Textual.

## Project Structure

```
src/oakwood/
├── app.py                  # Textual App subclass, entry point, DB lifecycle
├── oakwood.tcss            # Warm dark theme (amber/gold on dark brown)
├── database.py             # SQLite operations
├── models.py               # Book dataclass (26 fields)
├── settings.py             # Settings dataclass, load/save JSON from ~/.oakwood/
├── importer.py             # Bookshelf CSV import logic
├── openlibrary.py          # Open Library API client for verification
├── screens/
│   ├── main.py             # Stats + search + DataTable of recent books
│   ├── book_detail.py      # Full book info panel
│   ├── verify.py           # Multi-phase: loading -> comparison -> field resolution -> summary
│   └── import_csv.py       # File path input + progress + per-book log
└── widgets/
    ├── stats_panel.py      # "N books | M shelves" bar
    └── book_table.py       # DataTable wrapper with ISBN tracking + BookSelected message
```

## Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode
pip install -e .

# Run TUI
oakwood
```

## Screens

- **MainScreen** (default) - Stats bar, search input, book table sorted by date added. Keys: `/` search, `i` import, `q` quit, Enter for details.
- **BookDetailScreen** - Full book info panel. Keys: `v` verify, Escape back.
- **VerifyScreen** - Multi-phase verification against Open Library API. Keys: `1` keep local, `2` use API, `s` skip, Escape back.
- **ImportScreen** - CSV file path input + import button + per-book progress log. Escape back.

## Dependencies

- textual - Full-screen TUI framework
- pandas - CSV parsing

## Settings

Configuration is stored in `~/.oakwood/oakwood-settings.json`. The file is created with defaults on first launch. Users edit it directly and restart the app to apply changes.

```json
{
  "db_path": "data/oakwood.db",
  "covers_path": ""
}
```

Relative paths are resolved from `~/.oakwood/`. Absolute paths and `~` expansion are supported.

## Database

SQLite database at `~/.oakwood/data/oakwood.db` by default (configurable via `db_path` in settings). Created automatically if it does not exist. Uses ISBN as unique identifier for duplicate detection during import. Books have `verified` and `last_verified` fields for tracking verification status. Connection uses `check_same_thread=False` for Textual worker thread compatibility.

## Verification

The verify flow compares book data against Open Library API. Compares 7 fields: title, authors, page_count, publisher, published_at, categories, description. User can choose to keep local value, use API value, or skip each differing field. Books are marked as verified with timestamp after completion.

## CSV Format

Imports from Bookshelf iOS app exports. Key fields: Book Id, ISBN, Title, Authors, Bookshelf, Publisher, Published At, Page Count, Format, Categories, Description, Series, Volume, Date added.

## Documentation

All Python code uses **numpydoc**-style docstrings. Follow these conventions when adding or updating docstrings:

- **Module docstrings** — one-line summary, optionally followed by a blank line and an extended description.
- **Class docstrings** — one-line summary, optional extended description, then an `Attributes` section for dataclasses and any class with notable public attributes.
- **Function / method docstrings** — one-line summary, optional extended description, then applicable sections in this order: `Parameters`, `Returns` (or `Yields`), `Raises`, `Notes`, `Examples`.
- Simple one-line docstrings are acceptable for trivial methods (e.g. `action_go_back`, `action_quit`).
- Use `"""` triple-double-quotes, with the opening quotes on the same line as the summary.

### Numpydoc section format

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

- Parameter types should match the type annotations but use prose-friendly forms (e.g. `str or None` instead of `Optional[str]`, `list of str` instead of `list[str]`).
- Use double backticks for inline code references in descriptions (e.g. `` ``None`` ``, `` ``Book`` ``).
- Do not repeat the function signature in the docstring body.
- Keep descriptions concise — one to two sentences per parameter is usually enough.
