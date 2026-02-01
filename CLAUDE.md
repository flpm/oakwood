# Oakwood Book Catalogue

A full-screen TUI for managing a personal book catalogue with support for importing books from Bookshelf iOS app CSV exports. Built with Textual.

## Project Structure

```
src/oakwood/
├── app.py                  # Textual App subclass, entry point, DB lifecycle
├── oakwood.tcss            # Warm dark theme (amber/gold on dark brown)
├── database.py             # SQLite operations
├── models.py               # Book dataclass (26 fields)
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

## Database

SQLite database at `data/oakwood.db`. Uses ISBN as unique identifier for duplicate detection during import. Books have `verified` and `last_verified` fields for tracking verification status. Connection uses `check_same_thread=False` for Textual worker thread compatibility.

## Verification

The verify flow compares book data against Open Library API. Compares 7 fields: title, authors, page_count, publisher, published_at, categories, description. User can choose to keep local value, use API value, or skip each differing field. Books are marked as verified with timestamp after completion.

## CSV Format

Imports from Bookshelf iOS app exports. Key fields: Book Id, ISBN, Title, Authors, Bookshelf, Publisher, Published At, Page Count, Format, Categories, Description, Series, Volume, Date added.
