# Oakwood Book Catalogue

A CLI tool for managing a personal book catalogue with support for importing books from Bookshelf iOS app CSV exports.

## Project Structure

```
books/
├── src/oakwood/
│   ├── cli.py          # Click-based CLI entry point
│   ├── ui.py           # Rich UI components (tables, panels, prompts)
│   ├── database.py     # SQLite operations
│   ├── models.py       # Book dataclass (26 fields)
│   ├── importer.py     # Bookshelf CSV import logic
│   └── openlibrary.py  # Open Library API client for verification
├── data/
│   ├── bookshelf/      # CSV exports from Bookshelf app
│   └── oakwood.db      # SQLite database (created on first run)
├── notebooks/          # Jupyter notebooks for analysis
└── .venv/              # Virtual environment
```

## Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode
pip install -e .

# Run CLI
oakwood --help
```

## Commands

- `oakwood` - Interactive menu mode
- `oakwood import <csv>` - Import books from Bookshelf CSV
- `oakwood list [--shelf NAME]` - List books
- `oakwood stats` - Collection statistics
- `oakwood info <isbn>` - Book details
- `oakwood search <query>` - Search by title/author/ISBN
- `oakwood verify <isbn>` - Verify book against Open Library API

## Dependencies

- click - CLI framework
- rich - Terminal UI (tables, spinners, colors)
- pandas - CSV parsing

## Database

SQLite database at `data/oakwood.db`. Uses ISBN as unique identifier for duplicate detection during import. Books have `verified` and `last_verified` fields for tracking verification status.

## Verification

The `verify` command compares book data against Open Library API. Compares 7 fields: title, authors, page_count, publisher, published_at, categories, description. User can choose to keep local value, use API value, or skip each differing field. Books are marked as verified with timestamp after completion.

## CSV Format

Imports from Bookshelf iOS app exports. Key fields: Book Id, ISBN, Title, Authors, Bookshelf, Publisher, Published At, Page Count, Format, Categories, Description, Series, Volume, Date added.
