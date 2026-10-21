"""Atomic JSON, CSV, and JSONL persistence with OS locks, backups, and corruption recovery."""

import asyncio
import csv
import fcntl
import json
import logging
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("app.core.file_store")

# In-process locks per file path
_PATH_LOCKS: dict[str, asyncio.Lock] = {}
_META_LOCK = asyncio.Lock()


async def _get_path_lock(path: Path) -> asyncio.Lock:
    resolved = str(path.resolve())
    async with _META_LOCK:
        if resolved not in _PATH_LOCKS:
            _PATH_LOCKS[resolved] = asyncio.Lock()
        return _PATH_LOCKS[resolved]


class FileStore:
    """Durability engine: atomic writes, OS file locks, 5 rolling backups, and corruption recovery."""

    def __init__(self, max_backups: int = 5) -> None:
        self.max_backups = max_backups

    def _get_backup_dir(self, target_file: Path) -> Path:
        backup_dir = target_file.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _rotate_backups(self, target_file: Path) -> None:
        """Rotate rolling backups, keeping at most max_backups."""
        if not target_file.exists():
            return
        backup_dir = self._get_backup_dir(target_file)
        stem = target_file.name

        # Delete oldest if at limit
        oldest = backup_dir / f"{stem}.{self.max_backups}.bak"
        if oldest.exists():
            oldest.unlink()

        # Shift existing
        for i in range(self.max_backups - 1, 0, -1):
            src = backup_dir / f"{stem}.{i}.bak"
            dst = backup_dir / f"{stem}.{i + 1}.bak"
            if src.exists():
                src.rename(dst)

        # Copy target to .1.bak
        shutil.copy2(target_file, backup_dir / f"{stem}.1.bak")

    async def write_json_atomic(
        self,
        target_file: Path,
        data: dict[str, Any] | list[Any],
        schema_version: int = 1,
        failure_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Write JSON atomically via temp file -> fsync -> os.replace with fcntl lock and rolling backups."""
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file = target_file.with_suffix(target_file.suffix + ".lock")

            # Attach schema_version if data is dict
            if isinstance(data, dict) and "schema_version" not in data:
                payload: dict[str, Any] = {"schema_version": schema_version, **data}
            else:
                payload = data  # type: ignore[assignment]

            serialized = json.dumps(payload, indent=2, ensure_ascii=False)

            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    # Create backup of current file before overwriting
                    if target_file.exists():
                        self._rotate_backups(target_file)

                    # Write to temp file in the same filesystem directory
                    temp_dir = target_file.parent
                    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
                        temp_path = Path(tf.name)
                        tf.write(serialized)
                        tf.flush()
                        os.fsync(tf.fileno())

                    # Atomic rename
                    os.replace(temp_path, target_file)
                except Exception as exc:
                    if failure_callback:
                        failure_callback("DATA_FILE_WRITE_ERROR", f"Failed atomic JSON write to {target_file}: {exc}")
                    raise
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def read_json_safe(
        self,
        target_file: Path,
        fallback_default: dict[str, Any] | list[Any] | None = None,
        failure_callback: Callable[[str, str], None] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Read JSON safely, falling back to newest valid backup on corruption."""
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            if not target_file.exists():
                if fallback_default is not None:
                    return fallback_default
                raise FileNotFoundError(f"File not found: {target_file}")

            lock_file = target_file.with_suffix(target_file.suffix + ".lock")
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_SH)
                try:
                    with open(target_file, encoding="utf-8") as f:
                        content = f.read()
                        return json.loads(content)  # type: ignore[no-any-return]
                except (json.JSONDecodeError, OSError) as exc:
                    # Corrupt file detected! Trigger recovery from rolling backups
                    if failure_callback:
                        failure_callback(
                            "DATA_FILE_CORRUPT",
                            f"Corrupt JSON file {target_file}: {exc}. Initiating backup restoration.",
                        )
                    recovered = self._recover_json_from_backup(target_file)
                    if recovered is not None:
                        return recovered
                    if fallback_default is not None:
                        return fallback_default
                    raise
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _recover_json_from_backup(self, target_file: Path) -> dict[str, Any] | list[Any] | None:
        backup_dir = self._get_backup_dir(target_file)
        stem = target_file.name
        for i in range(1, self.max_backups + 1):
            bak = backup_dir / f"{stem}.{i}.bak"
            if bak.exists():
                try:
                    with open(bak, encoding="utf-8") as f:
                        data = json.loads(f.read())
                        # Restore file from valid backup
                        shutil.copy2(bak, target_file)
                        logger.warning(f"Restored corrupt file {target_file} from backup {bak}")
                        return data  # type: ignore[no-any-return]
                except Exception:
                    continue
        return None

    async def update_json_atomic(
        self,
        target_file: Path,
        updater: Callable[[dict[str, Any]], dict[str, Any]],
        default_factory: Callable[[], dict[str, Any]],
        schema_version: int = 1,
    ) -> dict[str, Any]:
        """Perform a serialized, race-free read-modify-write on a JSON file."""
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file = target_file.with_suffix(target_file.suffix + ".lock")

            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    if target_file.exists():
                        try:
                            with open(target_file, encoding="utf-8") as f:
                                current_data: dict[str, Any] = json.loads(f.read())
                        except Exception:
                            recovered = self._recover_json_from_backup(target_file)
                            if isinstance(recovered, dict):
                                current_data = recovered
                            else:
                                current_data = default_factory()
                    else:
                        current_data = default_factory()

                    updated_data = updater(current_data)
                    if "schema_version" not in updated_data:
                        updated_data["schema_version"] = schema_version

                    self._rotate_backups(target_file)
                    temp_dir = target_file.parent
                    serialized = json.dumps(updated_data, indent=2, ensure_ascii=False)
                    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
                        temp_path = Path(tf.name)
                        tf.write(serialized)
                        tf.flush()
                        os.fsync(tf.fileno())

                    os.replace(temp_path, target_file)
                    return updated_data
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def append_jsonl(
        self,
        target_file: Path,
        records: list[dict[str, Any]],
        sync_immediately: bool = False,
    ) -> None:
        """Append lines to JSONL atomically with an exclusive OS lock."""
        if not records:
            return
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file = target_file.with_suffix(target_file.suffix + ".lock")
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    with open(target_file, "a", encoding="utf-8") as f:
                        for record in records:
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        f.flush()
                        if sync_immediately:
                            os.fsync(f.fileno())
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def read_jsonl_tolerant(
        self,
        target_file: Path,
        failure_callback: Callable[[str, str], None] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Read JSONL file tolerantly, skipping torn trailing lines and returning (records, torn_lines_count)."""
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            if not target_file.exists():
                return [], 0

            lock_file = target_file.with_suffix(target_file.suffix + ".lock")
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_SH)
                try:
                    records: list[dict[str, Any]] = []
                    torn_count = 0
                    with open(target_file, encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, start=1):
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue
                            try:
                                record = json.loads(line_stripped)
                                records.append(record)
                            except json.JSONDecodeError:
                                torn_count += 1
                                if failure_callback:
                                    failure_callback(
                                        "DATA_FILE_CORRUPT",
                                        f"Torn line {line_num} skipped in {target_file}",
                                    )
                    return records, torn_count
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def append_csv_rows(
        self,
        target_file: Path,
        headers: list[str],
        rows: list[dict[str, Any]],
        sync_immediately: bool = False,
    ) -> None:
        """Append rows to a CSV file. Writes header on initial file creation."""
        if not rows:
            return
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file = target_file.with_suffix(target_file.suffix + ".lock")
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    is_new = not target_file.exists() or target_file.stat().st_size == 0
                    with open(target_file, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                        if is_new:
                            writer.writeheader()
                        for row in rows:
                            writer.writerow(row)
                        f.flush()
                        if sync_immediately:
                            os.fsync(f.fileno())
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def read_csv_tolerant(
        self,
        target_file: Path,
        failure_callback: Callable[[str, str], None] | None = None,
    ) -> tuple[list[dict[str, str]], int]:
        """Read CSV keyed by column header, skipping torn trailing rows."""
        path_lock = await _get_path_lock(target_file)
        async with path_lock:
            if not target_file.exists():
                return [], 0

            lock_file = target_file.with_suffix(target_file.suffix + ".lock")
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_SH)
                try:
                    rows: list[dict[str, str]] = []
                    torn_count = 0
                    with open(target_file, newline="", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        if reader.fieldnames is None:
                            return [], 0
                        for row in reader:
                            # A torn line might have None as key or wrong column count
                            if None in row or len(row) < len(reader.fieldnames):
                                torn_count += 1
                                if failure_callback:
                                    failure_callback("DATA_FILE_CORRUPT", f"Torn CSV row in {target_file}")
                                continue
                            rows.append(row)
                    return rows, torn_count
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


file_store = FileStore()
