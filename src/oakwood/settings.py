"""Settings management for Oakwood catalogue.

Settings are persisted as JSON in ``_OAKWOOD_DIR/oakwood-settings.json``.
The file is created with defaults on first launch; users edit it directly
and restart the app to apply changes.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent.parent

_OAKWOOD_DIR = Path.home() / ".oakwood"
_DEFAULT_SETTINGS_PATH = _OAKWOOD_DIR / "oakwood-settings.json"


@dataclass
class Settings:
    """Application settings persisted as JSON.

    Relative paths are resolved from ``_OAKWOOD_DIR/``. Absolute paths and
    ``~`` expansion are supported.

    Attributes
    ----------
    db_path : str
        Path to the SQLite database file.
    covers_path : str
        Path to the book covers directory, or empty string if unused.
    """

    db_path: str = "data/oakwood.db"
    covers_path: str = ""

    def resolve_db_path(self) -> Path:
        """Resolve ``db_path`` to an absolute path.

        Relative paths are resolved from ``_OAKWOOD_DIR/``.

        Returns
        -------
        Path
            Absolute, resolved path to the database file.
        """
        p = Path(self.db_path).expanduser()
        if not p.is_absolute():
            p = _OAKWOOD_DIR / p
        return p.resolve()

    def resolve_covers_path(self) -> Optional[Path]:
        """Resolve ``covers_path`` to an absolute path.

        Relative paths are resolved from ``_OAKWOOD_DIR/``.

        Returns
        -------
        Path or None
            Absolute, resolved path to the covers directory, or ``None``
            if ``covers_path`` is empty.
        """
        if not self.covers_path:
            return None
        p = Path(self.covers_path).expanduser()
        if not p.is_absolute():
            p = _OAKWOOD_DIR / p
        return p.resolve()


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load settings from a JSON file.

    Creates the default settings file if it does not exist.

    Parameters
    ----------
    path : Path, optional
        Path to the settings file. Defaults to
        ``_OAKWOOD_DIR/oakwood-settings.json``.

    Returns
    -------
    Settings
        Loaded (or default) application settings.
    """
    path = path or _DEFAULT_SETTINGS_PATH
    if not path.exists():
        settings = Settings()
        save_settings(settings, path)
        return settings
    try:
        data = json.loads(path.read_text())
        return Settings(
            db_path=data.get("db_path", "data/oakwood.db"),
            covers_path=data.get("covers_path", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return Settings()


def save_settings(settings: Settings, path: Optional[Path] = None) -> None:
    """Write settings to a JSON file.

    Creates parent directories if they do not exist.

    Parameters
    ----------
    settings : Settings
        The settings to persist.
    path : Path, optional
        Destination file path. Defaults to
        ``_OAKWOOD_DIR/oakwood-settings.json``.
    """
    path = path or _DEFAULT_SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2) + "\n")
