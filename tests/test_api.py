"""API contract and validation regressions."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


class TaskAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "tasks.sqlite3"
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TASK_MANAGER_API_KEY", None)
            self.client = TestClient(create_app(self.db))

    def add(self, title="Revisar API", **values):
        return self.client.post("/tasks", json={"title": title, **values})

    def test_health_and_docs(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        spec = self.client.get("/openapi.json").json()
        self.assertIn("/tasks", spec["paths"])
        self.assertIn("APIKeyHeader", spec["components"]["securitySchemes"])

    def test_crud_and_restart(self):
        created = self.add("  Revisar portfólio  ")
        self.assertEqual(created.status_code, 201)
        task = created.json()
        self.assertEqual(task["title"], "Revisar portfólio")
        self.assertFalse(task["completed"])
        self.assertEqual(self.client.get("/tasks").json(), [task])
        self.assertEqual(self.client.get(f"/tasks/{task['id']}").json(), task)
        self.assertTrue(self.db.is_file())
        restarted = TestClient(create_app(self.db))
        self.assertEqual(restarted.get("/tasks").json(), [task])
        changed = restarted.patch(f"/tasks/{task['id']}", json={"completed": True})
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(changed.json()["completed"])
        self.assertEqual(restarted.delete(f"/tasks/{task['id']}").status_code, 204)
        self.assertEqual(restarted.get("/tasks").json(), [])

    def test_create_completed_and_patch_title(self):
        task = self.add("Primeira", completed=True).json()
        result = self.client.patch(f"/tasks/{task['id']}", json={"title": "  Segunda  "})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["title"], "Segunda")
        self.assertTrue(result.json()["completed"])

    def test_patch_two_fields(self):
        task_id = self.add().json()["id"]
        result = self.client.patch(
            f"/tasks/{task_id}", json={"title": "Novo título", "completed": True}
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["title"], "Novo título")
        self.assertTrue(result.json()["completed"])

    def test_blank_titles(self):
        for title in ["", " ", "\n  \t"]:
            with self.subTest(title=title):
                self.assertEqual(self.add(title).status_code, 422)

    def test_title_length(self):
        self.assertEqual(self.add("x" * 200).status_code, 201)
        self.assertEqual(self.add("x" * 201).status_code, 422)

    def test_invalid_create_bodies(self):
        for data in [{}, {"title": None}, {"title": 123}, {"title": "a", "extra": 1}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/tasks", json=data).status_code, 422)

    def test_invalid_patch_bodies(self):
        task_id = self.add().json()["id"]
        for data in [{}, {"title": "  "}, {"completed": None},
                     {"title": None}, {"title": "a", "extra": 1}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.patch(f"/tasks/{task_id}", json=data).status_code, 422)
        self.assertEqual(self.client.get(f"/tasks/{task_id}").json()["title"], "Revisar API")

    def test_missing_ids(self):
        self.assertEqual(self.client.get("/tasks/999").status_code, 404)
        self.assertEqual(self.client.patch("/tasks/999", json={"completed": True}).status_code, 404)
        self.assertEqual(self.client.delete("/tasks/999").status_code, 404)

    def test_invalid_ids(self):
        for value in ["0", "-1", "abc"]:
            with self.subTest(value=value):
                self.assertEqual(self.client.get(f"/tasks/{value}").status_code, 422)

    def test_filter_and_pagination(self):
        for i in range(5):
            self.add(f"Tarefa {i}", completed=i % 2 == 0)
        self.assertEqual(len(self.client.get("/tasks").json()), 5)
        filtered = self.client.get("/tasks?completed=true").json()
        self.assertEqual(len(filtered), 3)
        self.assertTrue(all(t["completed"] for t in filtered))
        page = self.client.get("/tasks?limit=2&offset=1").json()
        self.assertEqual([t["title"] for t in page], ["Tarefa 1", "Tarefa 2"])
        self.assertEqual(len(self.client.get("/tasks?offset=4").json()), 1)

    def test_invalid_filters(self):
        for value in ["limit=0", "limit=101", "limit=abc", "offset=-1", "completed=maybe"]:
            with self.subTest(value=value):
                self.assertEqual(self.client.get(f"/tasks?{value}").status_code, 422)

    def test_delete_empty_body_and_repeat(self):
        task_id = self.add().json()["id"]
        response = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.delete(f"/tasks/{task_id}").status_code, 404)

    def test_optional_api_key(self):
        with patch.dict(os.environ, {"TASK_MANAGER_API_KEY": "test-value"}):
            client = TestClient(create_app(Path(self.temp.name) / "secured.db"))
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/tasks").status_code, 401)
            self.assertEqual(client.post("/tasks", json={"title": "x"}).status_code, 401)
            self.assertEqual(client.get("/tasks", headers={"X-API-Key": "wrong"}).status_code, 401)
            headers = {"X-API-Key": "test-value"}
            self.assertEqual(client.post("/tasks", json={"title": "x"}, headers=headers).status_code, 201)
            self.assertEqual(client.get("/tasks", headers=headers).status_code, 200)

    def test_empty_api_key_configuration(self):
        with patch.dict(os.environ, {"TASK_MANAGER_API_KEY": " "}):
            with self.assertRaises(ValueError):
                create_app(Path(self.temp.name) / "bad.db")

    def test_explicit_db_path_overrides_environment(self):
        with patch.dict(os.environ, {"TASK_MANAGER_DB_PATH": "/invalid/location/db.sqlite3"}):
            self.assertEqual(TestClient(create_app(self.db)).get("/tasks").status_code, 200)


if __name__ == "__main__":
    unittest.main()
