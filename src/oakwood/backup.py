"""Backup and restore logic for Oakwood catalogue.

Creates and restores ``.tar.gz`` archives containing the SQLite database
and, optionally, the book covers directory. Backups are stored in a
``backups/`` subdirectory next to the database file.
"""

import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


@dataclass
class BackupInfo:
    """Metadata for a single backup archive.

    Attributes
    ----------
    path : Path
        Absolute path to the ``.tar.gz`` file.
    filename : str
        Basename of the archive.
    size_bytes : int
        File size in bytes.
    created : datetime
        Timestamp parsed from the filename.
    """

    path: Path
    filename: str
    size_bytes: int
    created: datetime


def get_backups_dir(db_path: Path) -> Path:
    """Return the backups directory, creating it if needed.

    The directory is ``<db_parent>/backups/``.

    Parameters
    ----------
    db_path : Path
        Absolute path to the SQLite database file.

    Returns
    -------
    Path
        Absolute path to the backups directory.
    """
    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def list_backups(db_path: Path) -> list[BackupInfo]:
    """List existing backups, sorted newest first.

    Parses timestamps from filenames matching the pattern
    ``oakwood-backup-YYYY-MM-DD-HHMMSS.tar.gz``.

    Parameters
    ----------
    db_path : Path
        Absolute path to the SQLite database file.

    Returns
    -------
    list of BackupInfo
        Backup metadata sorted by creation time, newest first.
    """
    backups_dir = get_backups_dir(db_path)
    backups = []
    for p in backups_dir.glob("oakwood-backup-*.tar.gz"):
        # Parse timestamp from filename: oakwood-backup-YYYY-MM-DD-HHMMSS.tar.gz
        stem = p.name.replace("oakwood-backup-", "").replace(".tar.gz", "")
        try:
            created = datetime.strptime(stem, "%Y-%m-%d-%H%M%S")
        except ValueError:
            continue
        backups.append(BackupInfo(
            path=p,
            filename=p.name,
            size_bytes=p.stat().st_size,
            created=created,
        ))
    backups.sort(key=lambda b: b.created, reverse=True)
    return backups


def create_backup(
    db_path: Path,
    covers_path: Optional[Path] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> BackupInfo:
    """Create a ``.tar.gz`` backup of the database and optional covers.

    The archive is written to ``<db_parent>/backups/`` with a timestamped
    filename.

    Parameters
    ----------
    db_path : Path
        Absolute path to the SQLite database file.
    covers_path : Path or None
        Absolute path to the covers directory, or ``None`` to skip.
    on_progress : callable, optional
        Callback invoked with status messages during the operation.

    Returns
    -------
    BackupInfo
        Metadata for the newly created backup.
    """
    backups_dir = get_backups_dir(db_path)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"oakwood-backup-{timestamp}.tar.gz"
    backup_path = backups_dir / filename

    if on_progress:
        on_progress(f"Creating backup {filename}...")

    with tarfile.open(backup_path, "w:gz") as tar:
        if on_progress:
            on_progress(f"Adding database ({db_path.name})...")
        tar.add(db_path, arcname="oakwood.db")

        if covers_path and covers_path.is_dir():
            if on_progress:
                on_progress(f"Adding covers directory...")
            tar.add(covers_path, arcname="covers")

    info = BackupInfo(
        path=backup_path,
        filename=filename,
        size_bytes=backup_path.stat().st_size,
        created=datetime.strptime(timestamp, "%Y-%m-%d-%H%M%S"),
    )

    if on_progress:
        on_progress(f"Backup complete: {filename} ({format_size(info.size_bytes)})")

    return info


def restore_backup(
    backup_path: Path,
    db_path: Path,
    covers_path: Optional[Path] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> None:
    """Restore a backup archive over the current database and covers.

    The current database is renamed to ``oakwood.db.pre-restore`` before
    extraction. The caller is responsible for closing the database
    connection before calling this function and reopening it after.

    Parameters
    ----------
    backup_path : Path
        Path to the ``.tar.gz`` backup archive.
    db_path : Path
        Absolute path to the current SQLite database file.
    covers_path : Path or None
        Absolute path to the covers directory, or ``None`` to skip
        cover restoration.
    on_progress : callable, optional
        Callback invoked with status messages during the operation.

    Raises
    ------
    FileNotFoundError
        If *backup_path* does not exist.
    tarfile.TarError
        If the archive is corrupt or unreadable.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    if on_progress:
        on_progress("Extracting backup to temporary directory...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(tmp_path, filter="data")

        extracted_db = tmp_path / "oakwood.db"
        if not extracted_db.exists():
            raise FileNotFoundError("Backup archive does not contain oakwood.db")

        # Rename current DB for safety
        pre_restore = db_path.with_suffix(".db.pre-restore")
        if db_path.exists():
            if on_progress:
                on_progress(f"Saving current database as {pre_restore.name}...")
            shutil.copy2(db_path, pre_restore)

        # Copy extracted DB into place
        if on_progress:
            on_progress("Restoring database...")
        shutil.copy2(extracted_db, db_path)

        # Restore covers if present in archive and covers_path is configured
        extracted_covers = tmp_path / "covers"
        if covers_path and extracted_covers.is_dir():
            if on_progress:
                on_progress("Restoring covers directory...")
            if covers_path.exists():
                shutil.rmtree(covers_path)
            shutil.copytree(extracted_covers, covers_path)

    if on_progress:
        on_progress("Restore complete.")


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string.

    Parameters
    ----------
    size_bytes : int
        File size in bytes.

    Returns
    -------
    str
        Formatted string (e.g. ``"1.2 MB"``, ``"340 KB"``).
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
