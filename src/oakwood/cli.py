"""CLI entry point for Oakwood book catalogue."""

from datetime import date
from pathlib import Path
from typing import Optional

import click

from . import database, importer, ui
from .database import (
    get_all_books,
    get_all_shelves,
    get_book_by_isbn,
    get_book_count,
    get_connection,
    get_format_counts,
    get_shelf_counts,
    init_db,
    search_books,
    update_book_fields,
)
from .openlibrary import OpenLibraryError, fetch_book


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Oakwood - A CLI for managing your book catalogue."""
    if ctx.invoked_subcommand is None:
        interactive_mode()


@main.command("import")
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
def import_cmd(csv_file: Path) -> None:
    """Import books from a Bookshelf CSV export."""
    conn = get_connection()
    init_db(conn)

    with ui.create_spinner("Importing books..."):
        added, skipped = importer.import_csv(csv_file, conn)

    conn.close()
    ui.print_import_summary(added, skipped)


@main.command("import-verbose")
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
def import_verbose_cmd(csv_file: Path) -> None:
    """Import books from a Bookshelf CSV export with per-book output."""
    conn = get_connection()
    init_db(conn)

    def on_book(book, is_new):
        if is_new:
            ui.print_success(f"Added: {book.display_title(60)}")
        else:
            ui.print_skip(f"Skipped: {book.display_title(60)} (duplicate)")

    added, skipped = importer.import_csv(csv_file, conn, on_book=on_book)
    conn.close()
    ui.print_import_summary(added, skipped)


@main.command("list")
@click.option("--shelf", "-s", help="Filter by shelf name")
def list_cmd(shelf: Optional[str]) -> None:
    """List all books in the catalogue."""
    conn = get_connection()
    init_db(conn)

    books = get_all_books(conn, shelf=shelf)
    ui.display_book_table(books)
    conn.close()


@main.command("stats")
def stats_cmd() -> None:
    """Show collection statistics."""
    conn = get_connection()
    init_db(conn)

    total = get_book_count(conn)
    shelf_counts = get_shelf_counts(conn)
    format_counts = get_format_counts(conn)

    ui.display_stats(total, shelf_counts, format_counts)
    conn.close()


@main.command("info")
@click.argument("isbn")
def info_cmd(isbn: str) -> None:
    """Show detailed info for a specific book."""
    conn = get_connection()
    init_db(conn)

    book = get_book_by_isbn(conn, isbn)
    if book:
        ui.display_book_info(book)
    else:
        ui.print_error(f"No book found with ISBN: {isbn}")

    conn.close()


@main.command("search")
@click.argument("query")
def search_cmd(query: str) -> None:
    """Search books by title, author, or ISBN."""
    conn = get_connection()
    init_db(conn)

    books = search_books(conn, query)
    ui.display_book_table(books)
    conn.close()


# Fields that can be verified against Open Library
VERIFIABLE_FIELDS = [
    "title",
    "authors",
    "page_count",
    "publisher",
    "published_at",
    "categories",
    "description",
]


def _run_verification(conn, isbn: str) -> None:
    """Run the verification process for a book."""
    # Fetch local book
    book = get_book_by_isbn(conn, isbn)
    if not book:
        ui.print_error(f"No book found with ISBN: {isbn}")
        return

    # Fetch from Open Library
    with ui.create_spinner("Fetching from Open Library..."):
        try:
            api_book = fetch_book(isbn)
        except OpenLibraryError as e:
            ui.print_error(str(e))
            return

    # Compare fields and build differences list
    differences = []
    for field in VERIFIABLE_FIELDS:
        local_val = getattr(book, field)
        api_val = getattr(api_book, field)

        # Convert to strings for comparison
        local_str = str(local_val) if local_val else ""
        api_str = str(api_val) if api_val else ""

        # Only add to differences if API has a value and they differ
        if api_val is not None and local_str != api_str:
            differences.append((field, local_str, api_str))

    # If no differences, mark as verified and show success
    if not differences:
        update_book_fields(conn, isbn, {"verified": True, "last_verified": date.today()})
        ui.print_success("All verifiable fields match. Book marked as verified.")
        return

    # Display comparison table
    ui.display_comparison_table(differences, book.title)

    # For each difference, prompt user for choice
    updates = {}
    updated_fields = []
    skipped_fields = []

    for field, local_val, api_val in differences:
        choice = ui.prompt_field_choice(field, local_val, api_val)

        if choice == "q":
            ui.print_info("Verification cancelled.")
            return
        elif choice == "2":
            # Use API value
            api_typed = getattr(api_book, field)
            updates[field] = api_typed
            updated_fields.append(field.replace("_", " ").title())
        else:
            # Keep local or skip
            skipped_fields.append(field.replace("_", " ").title())

    # Apply updates and mark as verified
    updates["verified"] = True
    updates["last_verified"] = date.today()
    update_book_fields(conn, isbn, updates)

    # Show summary
    ui.display_verification_summary(
        updated_fields, skipped_fields, str(date.today())
    )


@main.command("verify")
@click.argument("isbn")
def verify_cmd(isbn: str) -> None:
    """Verify book data against Open Library API."""
    conn = get_connection()
    init_db(conn)

    _run_verification(conn, isbn)

    conn.close()


def interactive_mode() -> None:
    """Run the interactive menu mode."""
    conn = get_connection()
    init_db(conn)

    ui.console.print("[bold]Oakwood[/bold] Book Catalogue\n")

    total = get_book_count(conn)
    if total > 0:
        ui.print_info(f"{total} books in collection")

    options = [
        ("import", "Import books from CSV"),
        ("list", "List all books"),
        ("stats", "Show statistics"),
        ("search", "Search books"),
        ("info", "Book details (by ISBN)"),
        ("verify", "Verify book (by ISBN)"),
    ]

    while True:
        choice = ui.interactive_menu(options)

        if choice is None:
            break

        if choice == "import":
            csv_path = click.prompt("CSV file path", type=click.Path(exists=True))
            with ui.create_spinner("Importing books..."):
                added, skipped = importer.import_csv(Path(csv_path), conn)
            ui.print_import_summary(added, skipped)

        elif choice == "list":
            shelves = get_all_shelves(conn)
            shelf = ui.prompt_shelf(shelves)
            books = get_all_books(conn, shelf=shelf)
            ui.display_book_table(books)

        elif choice == "stats":
            total = get_book_count(conn)
            shelf_counts = get_shelf_counts(conn)
            format_counts = get_format_counts(conn)
            ui.display_stats(total, shelf_counts, format_counts)

        elif choice == "search":
            query = ui.prompt_search()
            if query:
                books = search_books(conn, query)
                ui.display_book_table(books)

        elif choice == "info":
            isbn = ui.prompt_isbn()
            if isbn:
                book = get_book_by_isbn(conn, isbn)
                if book:
                    ui.display_book_info(book)
                else:
                    ui.print_error(f"No book found with ISBN: {isbn}")

        elif choice == "verify":
            isbn = ui.prompt_isbn()
            if isbn:
                _run_verification(conn, isbn)

    conn.close()
    ui.console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    main()
