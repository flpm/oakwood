"""Book edit screen for modifying book fields.

Renders a form with grouped sections for all editable book fields.
Validates input, computes a diff against the original values, and
persists only the changed fields.
"""

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Label, Static, TextArea

from ..database import book_exists, get_book_by_isbn, update_book_fields
from ..models import Book

# Field definitions: (field_name, label, widget_type)
# widget_type: "input", "textarea", "checkbox", "int", "date"
_FIELD_SECTIONS = [
    (
        "Core",
        [
            ("title", "Title", "input"),
            ("subtitle", "Subtitle", "input"),
            ("isbn", "ISBN", "input"),
            ("book_id", "Book ID", "input"),
            ("bookshelf", "Bookshelf", "input"),
            ("date_added", "Date Added", "date"),
        ],
    ),
    (
        "Metadata",
        [
            ("authors", "Authors", "input"),
            ("publisher", "Publisher", "input"),
            ("published_at", "Published", "date"),
            ("page_count", "Pages", "int"),
            ("language", "Language", "input"),
            ("format", "Format", "input"),
            ("categories", "Categories", "input"),
        ],
    ),
    (
        "Series",
        [
            ("series", "Series", "input"),
            ("volume", "Volume", "input"),
        ],
    ),
    (
        "Contributors",
        [
            ("editors", "Editors", "input"),
            ("translators", "Translators", "input"),
            ("illustrators", "Illustrators", "input"),
        ],
    ),
    (
        "Description",
        [
            ("description", "Description", "textarea"),
        ],
    ),
    (
        "Status",
        [
            ("read", "Read", "checkbox"),
            ("wishlist", "Wishlist", "checkbox"),
            ("signed", "Signed", "checkbox"),
            ("pages_read", "Pages Read", "int"),
            ("number_of_copies", "Copies", "int"),
        ],
    ),
    (
        "Verification",
        [
            ("verified", "Verified", "checkbox"),
            ("last_verified", "Last Verified", "date"),
        ],
    ),
]


def _book_field_value(book: Book, field: str) -> str | bool | int:
    """Get a field value from a Book, formatted for widget display.

    Parameters
    ----------
    book : Book
        The book instance.
    field : str
        Attribute name on the ``Book`` dataclass.

    Returns
    -------
    str or bool or int
        The value formatted for display: dates become ISO strings,
        ``None`` becomes ``""``, and all other values are passed through.
    """
    value = getattr(book, field)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if value is None:
        return ""
    return str(value)


class BookEditScreen(Screen):
    """Form screen for editing book fields.

    Groups fields into sections and renders appropriate input widgets
    (text input, textarea, checkbox) for each. Only changed fields are
    persisted on save.

    Parameters
    ----------
    isbn : str
        ISBN of the book to edit.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, isbn: str) -> None:
        super().__init__()
        self.isbn = isbn
        self._book: Book | None = None
        self._original: dict[str, str | bool | int] = {}

    def compose(self) -> ComposeResult:
        """Build the edit form with sections, inputs, and action buttons."""
        with VerticalScroll(id="edit-container"):
            yield Static("Edit Book", id="edit-heading")
            yield Static("", id="edit-error")

            for section_name, fields in _FIELD_SECTIONS:
                yield Static(
                    f"[bold #d4a04a]{section_name}[/bold #d4a04a]",
                    classes="edit-section-header",
                )
                for field_name, label, widget_type in fields:
                    if widget_type == "checkbox":
                        with Horizontal(classes="edit-field-row"):
                            yield Checkbox(
                                label,
                                id=f"edit-{field_name}",
                                classes="edit-checkbox",
                            )
                    elif widget_type == "textarea":
                        yield Label(label, classes="edit-label")
                        yield TextArea(
                            id=f"edit-{field_name}",
                            classes="edit-textarea",
                            tab_behavior="focus",
                        )
                    else:
                        with Horizontal(classes="edit-field-row"):
                            yield Label(
                                f"{label:<16}", classes="edit-label-inline"
                            )
                            placeholder = ""
                            if widget_type == "date":
                                placeholder = "YYYY-MM-DD"
                            elif widget_type == "int":
                                placeholder = "0"
                            yield Input(
                                placeholder=placeholder,
                                id=f"edit-{field_name}",
                                classes="edit-input",
                            )

            with Horizontal(id="edit-buttons"):
                yield Button("Save", id="edit-save", variant="primary")
                yield Button("Cancel", id="edit-cancel")

        yield Footer()

    def on_mount(self) -> None:
        """Load the book and populate all form widgets."""
        self._book = get_book_by_isbn(self.app.db, self.isbn)
        if not self._book:
            self.query_one("#edit-error").update(
                "[#c45a3a]Book not found[/#c45a3a]"
            )
            return
        self._populate_fields()

    def _populate_fields(self) -> None:
        """Fill all widgets with current book values."""
        for _section_name, fields in _FIELD_SECTIONS:
            for field_name, _label, widget_type in fields:
                value = _book_field_value(self._book, field_name)
                self._original[field_name] = value
                widget_id = f"edit-{field_name}"

                if widget_type == "checkbox":
                    self.query_one(f"#{widget_id}", Checkbox).value = bool(value)
                elif widget_type == "textarea":
                    self.query_one(f"#{widget_id}", TextArea).text = str(value)
                else:
                    self.query_one(f"#{widget_id}", Input).value = str(value)

    def _collect_values(self) -> dict[str, str | bool | int | date | None]:
        """Collect current widget values, converting to native Python types.

        Returns
        -------
        dict
            Mapping of field name to its current widget value. Integer
            and date fields are converted; invalid dates are stored as
            the sentinel string ``"INVALID"``.
        """
        values: dict = {}
        for _section_name, fields in _FIELD_SECTIONS:
            for field_name, _label, widget_type in fields:
                widget_id = f"edit-{field_name}"

                if widget_type == "checkbox":
                    values[field_name] = self.query_one(
                        f"#{widget_id}", Checkbox
                    ).value
                elif widget_type == "textarea":
                    values[field_name] = self.query_one(
                        f"#{widget_id}", TextArea
                    ).text
                elif widget_type == "int":
                    raw = self.query_one(f"#{widget_id}", Input).value.strip()
                    try:
                        values[field_name] = int(raw) if raw else 0
                    except ValueError:
                        values[field_name] = 0
                elif widget_type == "date":
                    raw = self.query_one(f"#{widget_id}", Input).value.strip()
                    if raw:
                        try:
                            values[field_name] = date.fromisoformat(raw)
                        except ValueError:
                            values[field_name] = "INVALID"
                    else:
                        values[field_name] = None
                else:
                    values[field_name] = self.query_one(
                        f"#{widget_id}", Input
                    ).value

        return values

    def _validate(
        self, values: dict,
    ) -> str | None:
        """Validate collected field values.

        Parameters
        ----------
        values : dict
            Output of ``_collect_values``.

        Returns
        -------
        str or None
            Human-readable error message, or ``None`` if valid.
        """
        # Required fields
        for field in ("title", "isbn", "bookshelf"):
            v = values.get(field, "")
            if isinstance(v, str) and not v.strip():
                return f"{field.capitalize()} cannot be empty"

        # Date validation
        for field in ("date_added", "published_at", "last_verified"):
            if values.get(field) == "INVALID":
                return f"Invalid date format for {field} (use YYYY-MM-DD)"

        # ISBN uniqueness check
        new_isbn = values.get("isbn", "")
        if isinstance(new_isbn, str):
            new_isbn = new_isbn.strip()
        if new_isbn != self.isbn and book_exists(self.app.db, new_isbn):
            return f"A book with ISBN {new_isbn} already exists"

        return None

    def _compute_diff(
        self, values: dict,
    ) -> dict:
        """Return only the fields whose values differ from the originals.

        Parameters
        ----------
        values : dict
            Output of ``_collect_values``.

        Returns
        -------
        dict
            Subset of *values* where the value has changed.
        """
        diff: dict = {}
        for field_name, new_value in values.items():
            old_value = self._original.get(field_name)
            # Normalize for comparison
            if isinstance(new_value, date):
                comparable_new = new_value.isoformat()
            elif isinstance(new_value, bool):
                comparable_new = new_value
            elif new_value is None:
                comparable_new = ""
            else:
                comparable_new = str(new_value)

            if isinstance(old_value, bool):
                comparable_old = old_value
            else:
                comparable_old = str(old_value) if old_value else ""

            if comparable_new != comparable_old:
                diff[field_name] = new_value

        return diff

    def _show_error(self, message: str) -> None:
        """Display a validation error in the error panel.

        Parameters
        ----------
        message : str
            Error text to display.
        """
        self.query_one("#edit-error").update(f"[#c45a3a]{message}[/#c45a3a]")

    def _clear_error(self) -> None:
        """Clear any displayed validation error."""
        self.query_one("#edit-error").update("")

    def action_save(self) -> None:
        """Save changes (bound to ``Ctrl+S``)."""
        self._do_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Save and Cancel button presses."""
        if event.button.id == "edit-save":
            self._do_save()
        elif event.button.id == "edit-cancel":
            self.action_cancel()

    def _do_save(self) -> None:
        """Validate, compute diff, and persist changed fields."""
        if not self._book:
            return

        self._clear_error()
        values = self._collect_values()

        error = self._validate(values)
        if error:
            self._show_error(error)
            return

        diff = self._compute_diff(values)
        if not diff:
            self.app.pop_screen()
            return

        # Handle ISBN change: update with old ISBN, store new one for detail screen
        new_isbn = diff.pop("isbn", None)

        if diff:
            update_book_fields(self.app.db, self.isbn, diff)

        if new_isbn is not None:
            new_isbn = new_isbn.strip() if isinstance(new_isbn, str) else new_isbn
            update_book_fields(self.app.db, self.isbn, {"isbn": new_isbn})
            self.app._edited_isbn = new_isbn

        self.app.pop_screen()

    def action_cancel(self) -> None:
        """Discard changes and return to the detail screen."""
        self.app.pop_screen()
