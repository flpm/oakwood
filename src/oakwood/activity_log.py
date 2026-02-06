"""Activity logging for tracking data modifications.

Provides a centralized logging system for all data modifications from both
TUI and MCP server. Logs are stored as JSON Lines in
``~/.oakwood/data/activity.log``.
"""

import fcntl
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_OAKWOOD_DIR = Path.home() / ".oakwood"
_LOG_PATH = _OAKWOOD_DIR / "data" / "activity.log"


@dataclass
class ActivityEntry:
    """A single activity log entry.

    Attributes
    ----------
    timestamp : str
        ISO 8601 timestamp with microseconds.
    action : str
        One of: ``create``, ``edit``, ``import``, ``backup``, ``restore``,
        ``verify``.
    source : str
        Either ``tui`` or ``mcp``.
    isbn : str or None
        Book ISBN when applicable.
    title : str or None
        Book title when applicable.
    details : dict
        Action-specific data.
    """

    timestamp: str
    action: str
    source: str
    isbn: Optional[str] = None
    title: Optional[str] = None
    details: dict = field(default_factory=dict)


def get_log_path() -> Path:
    """Return the path to the activity log file.

    Returns
    -------
    Path
        Path to ``~/.oakwood/data/activity.log``.
    """
    return _LOG_PATH


def log_activity(
    action: str,
    source: str,
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    **details,
) -> None:
    """Append an activity entry to the log file.

    Uses POSIX file locking to ensure safe concurrent writes from TUI and
    MCP server processes.

    Parameters
    ----------
    action : str
        The action type (``create``, ``edit``, ``import``, ``backup``,
        ``restore``, ``verify``).
    source : str
        The source of the action (``tui`` or ``mcp``).
    isbn : str, optional
        Book ISBN when applicable.
    title : str, optional
        Book title when applicable.
    **details
        Action-specific data to include in the log entry.
    """
    entry = ActivityEntry(
        timestamp=datetime.now().isoformat(),
        action=action,
        source=source,
        isbn=isbn,
        title=title,
        details=details,
    )

    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(asdict(entry), ensure_ascii=False) + "\n"

    with open(log_path, "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read_recent_activity(limit: int = 100) -> list[ActivityEntry]:
    """Read the most recent activity entries from the log.

    Parameters
    ----------
    limit : int
        Maximum number of entries to return.

    Returns
    -------
    list of ActivityEntry
        Recent entries sorted by timestamp descending (most recent first).
    """
    log_path = get_log_path()
    if not log_path.exists():
        return []

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(ActivityEntry(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Sort by timestamp descending and limit
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries[:limit]
