import tempfile
import unittest
from pathlib import Path

from app.storage import TaskStore


class TaskStoreTests(unittest.TestCase):
    def test_records_survive_store_recreation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data/tasks.sqlite3"
            first_store = TaskStore(path)
            created = first_store.create("Persistir", completed=True)

            restarted_store = TaskStore(path)
            self.assertEqual(restarted_store.get(created["id"]), created)
            self.assertEqual(restarted_store.list(), [created])
            self.assertTrue(restarted_store.delete(created["id"]))
            self.assertFalse(restarted_store.delete(created["id"]))


if __name__ == "__main__":
    unittest.main()
