"""SQLite regressions for existing databases and concurrent API traffic."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.storage import TaskStore


class SQLiteCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database = Path(self.temporary_directory.name) / "tasks.sqlite3"

    def test_existing_schema_is_preserved_without_dropping_rows(self) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
                    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO tasks (title, completed, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("Tarefa anterior", 1, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
        store = TaskStore(self.database)
        self.assertEqual(store.list()[0]["title"], "Tarefa anterior")
        self.assertTrue(store.list()[0]["completed"])
        self.assertEqual(store.create("Nova tarefa")["id"], 2)
        with sqlite3.connect(self.database) as connection:
            indexes = {row[1] for row in connection.execute("PRAGMA index_list(tasks)")}
        self.assertIn("idx_tasks_completed_id", indexes)

    def test_sql_metacharacters_are_stored_as_data(self) -> None:
        store = TaskStore(self.database)
        title = "'); DROP TABLE tasks; --"
        created = store.create(title)
        self.assertEqual(store.get(created["id"])["title"], title)
        self.assertEqual(store.create("Outra tarefa")["id"], 2)

    def test_concurrent_creates_keep_unique_ids_and_all_records(self) -> None:
        store = TaskStore(self.database)
        with ThreadPoolExecutor(max_workers=6) as executor:
            records = list(executor.map(lambda index: store.create(f"Tarefa {index}"), range(30)))
        self.assertEqual(len({record["id"] for record in records}), 30)
        self.assertEqual(len(store.list()), 30)
        self.assertEqual(
            {record["title"] for record in records}, {f"Tarefa {index}" for index in range(30)}
        )

    def test_concurrent_updates_do_not_corrupt_a_row(self) -> None:
        store = TaskStore(self.database)
        original = store.create("Antes")
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(
                    lambda index: store.update(original["id"], {"title": f"Versão {index}"}),
                    range(16),
                )
            )
        self.assertTrue(all(result is not None for result in results))
        latest = store.get(original["id"])
        self.assertIn(latest["title"], {f"Versão {index}" for index in range(16)})
        self.assertEqual(len(store.list()), 1)


if __name__ == "__main__":
    unittest.main()
