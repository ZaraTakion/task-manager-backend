"""Regression tests for non-destructive SQLite backup and restoration."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.storage import TaskStore
from scripts.backup_sqlite import backup_database


class SQLiteBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.source = self.directory / "original.sqlite3"
        self.backup = self.directory / "backups" / "snapshot.sqlite3"
        with sqlite3.connect(self.source) as connection:
            connection.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
            connection.execute("INSERT INTO tasks (title) VALUES (?)", ("Persistir dados",))

    def test_backup_is_consistent_and_restorable(self) -> None:
        self.assertEqual(backup_database(self.source, self.backup), self.backup)
        with sqlite3.connect(self.backup) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(
                connection.execute("SELECT title FROM tasks ORDER BY id").fetchall(),
                [("Persistir dados",)],
            )
        with sqlite3.connect(self.source) as connection:
            connection.execute("INSERT INTO tasks (title) VALUES ('Mais recente')")
        with sqlite3.connect(self.backup) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)

    def test_real_task_store_round_trip_restore(self) -> None:
        database = self.directory / "live-tasks.sqlite3"
        snapshot = self.directory / "live-tasks-backup.sqlite3"
        store = TaskStore(database)
        original = store.create("Antes do backup", completed=True)

        backup_database(database, snapshot)
        store.create("Após o backup")
        # No connection remains open: restore is deliberately offline.
        database.unlink()
        shutil.copyfile(snapshot, database)

        restored = TaskStore(database)
        self.assertEqual(restored.list(), [original])
        self.assertTrue(restored.get(original["id"])["completed"])

    def test_never_overwrites_existing_backup(self) -> None:
        backup_database(self.source, self.backup)
        original = self.backup.read_bytes()
        with self.assertRaises(FileExistsError):
            backup_database(self.source, self.backup)
        self.assertEqual(self.backup.read_bytes(), original)

    def test_missing_source_never_creates_source_or_backup(self) -> None:
        missing = self.directory / "missing.sqlite3"
        with self.assertRaises(FileNotFoundError):
            backup_database(missing, self.backup)
        self.assertFalse(missing.exists())
        self.assertFalse(self.backup.exists())

    def test_rejects_identical_source_and_destination(self) -> None:
        with self.assertRaises(ValueError):
            backup_database(self.source, self.source)
        self.assertTrue(self.source.exists())

    def test_corrupt_source_does_not_leave_partial_backup(self) -> None:
        invalid = self.directory / "corrupt.sqlite3"
        invalid.write_bytes(b"this is not a SQLite database")
        with self.assertRaises(sqlite3.DatabaseError):
            backup_database(invalid, self.backup)
        self.assertFalse(self.backup.exists())
        self.assertFalse(list(self.directory.rglob(".task-manager-backup-*")))


if __name__ == "__main__":
    unittest.main()
