"""Small SQLite persistence layer for task records."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


class TaskStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
                    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _as_dict(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        record = dict(row)
        record["completed"] = bool(record["completed"])
        return record

    def create(self, title: str, completed: bool = False) -> dict:
        now = self._now()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "INSERT INTO tasks (title, completed, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, int(completed), now, now),
            )
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            connection.commit()
        return self._as_dict(row)

    def list(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        return [self._as_dict(row) for row in rows]

    def get(self, task_id: int) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._as_dict(row)

    def update(self, task_id: int, changes: dict) -> dict | None:
        allowed = {"title", "completed"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return self.get(task_id)

        assignments = [f"{key} = ?" for key in values]
        parameters = [int(value) if key == "completed" else value for key, value in values.items()]
        assignments.append("updated_at = ?")
        parameters.extend([self._now(), task_id])
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", parameters
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            connection.commit()
        return self._as_dict(row)

    def delete(self, task_id: int) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            connection.commit()
        return cursor.rowcount > 0
