"""SQLite regression tests for data constraints and transactions."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.storage import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data" / "tasks.sqlite3"
        self.store = TaskStore(self.path)

    def test_records_survive_store_recreation(self):
        task = self.store.create("Persistir", completed=True)
        restarted = TaskStore(self.path)
        self.assertEqual(restarted.get(task["id"]), task)
        self.assertEqual(restarted.list(), [task])
        self.assertTrue(restarted.delete(task["id"]))
        self.assertFalse(restarted.delete(task["id"]))

    def test_filter_and_pagination(self):
        self.store.create("A", True)
        self.store.create("B", False)
        self.store.create("C", True)
        self.assertEqual([t["title"] for t in self.store.list(completed=True)], ["A", "C"])
        self.assertEqual([t["title"] for t in self.store.list(limit=1, offset=1)], ["B"])
        self.assertEqual([t["title"] for t in self.store.list(offset=2)], ["C"])

    def test_update_and_invalid_columns(self):
        task = self.store.create("A")
        self.assertTrue(self.store.update(task["id"], {"completed": True})["completed"])
        with self.assertRaises(ValueError):
            self.store.update(task["id"], {"created_at": "invalid"})
        with self.assertRaises(ValueError):
            self.store.update(task["id"], {})
        self.assertIsNone(self.store.update(999, {"completed": True}))

    def test_database_constraints(self):
        with sqlite3.connect(self.path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO tasks (title, completed, created_at, updated_at) VALUES (' ', 0, 'x', 'x')"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO tasks (title, completed, created_at, updated_at) VALUES ('ok', 2, 'x', 'x')"
                )

    def test_failed_update_preserves_data(self):
        record = self.store.create("Valid")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.update(record["id"], {"title": " "})
        self.assertEqual(self.store.get(record["id"]), record)

    def test_empty_database(self):
        self.assertEqual(self.store.list(), [])
        self.assertIsNone(self.store.get(123))


if __name__ == "__main__":
    unittest.main()
