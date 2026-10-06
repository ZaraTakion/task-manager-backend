import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


class TaskPersistenceAPITests(unittest.TestCase):
    def test_task_survives_application_restart_and_supports_crud(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "data/tasks.sqlite3"

            first_client = TestClient(create_app(database_path))
            created = first_client.post("/tasks", json={"title": "  Revisar portfólio  "})
            self.assertEqual(created.status_code, 201)
            task = created.json()
            self.assertEqual(task["title"], "Revisar portfólio")
            self.assertFalse(task["completed"])
            self.assertTrue(database_path.is_file())

            # A newly created app instance behaves like a process restart.
            restarted_client = TestClient(create_app(database_path))
            self.assertEqual(restarted_client.get("/tasks").json(), [task])
            self.assertEqual(restarted_client.get(f"/tasks/{task['id']}").status_code, 200)

            updated = restarted_client.patch(
                f"/tasks/{task['id']}", json={"completed": True}
            )
            self.assertEqual(updated.status_code, 200)
            self.assertTrue(updated.json()["completed"])

            deleted = restarted_client.delete(f"/tasks/{task['id']}")
            self.assertEqual(deleted.status_code, 204)
            self.assertEqual(restarted_client.get("/tasks").json(), [])

    def test_invalid_and_missing_tasks_return_client_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(Path(temp_dir) / "tasks.sqlite3"))
            self.assertEqual(client.post("/tasks", json={"title": "   "}).status_code, 422)
            self.assertEqual(client.get("/tasks/999").status_code, 404)
            self.assertEqual(client.patch("/tasks/999", json={"completed": True}).status_code, 404)
            self.assertEqual(client.delete("/tasks/999").status_code, 404)


if __name__ == "__main__":
    unittest.main()
