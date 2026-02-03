"""Settings management for Oakwood catalogue."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent.parent

_OAKWOOD_DIR = Path.home() / ".oakwood"
_DEFAULT_SETTINGS_PATH = _OAKWOOD_DIR / "oakwood-settings.json"


@dataclass
class Settings:
    """Application settings persisted as JSON."""

    db_path: str = "data/oakwood.db"
    covers_path: str = ""

    def resolve_db_path(self) -> Path:
        """Resolve db_path to an absolute Path (relative to ~/.oakwood/)."""
        p = Path(self.db_path).expanduser()
        if not p.is_absolute():
            p = _OAKWOOD_DIR / p
        return p.resolve()

    def resolve_covers_path(self) -> Optional[Path]:
        """Resolve covers_path to an absolute Path (relative to ~/.oakwood/), or None if empty."""
        if not self.covers_path:
            return None
        p = Path(self.covers_path).expanduser()
        if not p.is_absolute():
            p = _OAKWOOD_DIR / p
        return p.resolve()


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load settings from JSON file. Creates default file if missing."""
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
    """Write settings to JSON file."""
    path = path or _DEFAULT_SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2) + "\n")
