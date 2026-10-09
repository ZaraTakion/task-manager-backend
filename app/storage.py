"""SQLite repository with parameterized queries and short transactions."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class TaskRow(TypedDict):
    id: int
    title: str
    completed: bool
    created_at: str
    updated_at: str


class TaskStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_completed_id ON tasks(completed, id)"
            )
            connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _as_dict(row: sqlite3.Row | None) -> TaskRow | None:
        if row is None:
            return None
        record = dict(row)
        record["completed"] = bool(record["completed"])
        return record

    def create(self, title: str, completed: bool = False) -> TaskRow:
        now = self._now()
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO tasks (title, completed, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (title, int(completed), now, now),
                )
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
        result = self._as_dict(row)
        if result is None:
            raise RuntimeError("Falha ao recuperar tarefa recém-criada.")
        return result

    def list(
        self, completed: bool | None = None, limit: int | None = None, offset: int = 0
    ) -> list[TaskRow]:
        query = "SELECT * FROM tasks"
        params: list[int] = []
        if completed is not None:
            query += " WHERE completed = ?"
            params.append(int(completed))
        query += " ORDER BY id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        elif offset:
            query += " LIMIT -1"
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [record for row in rows if (record := self._as_dict(row)) is not None]

    def get(self, task_id: int) -> TaskRow | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._as_dict(row)

    def update(self, task_id: int, changes: dict[str, str | bool]) -> TaskRow | None:
        allowed = {"title", "completed"}
        if not changes or not changes.keys() <= allowed:
            raise ValueError("Campos de atualização inválidos.")
        if any(value is None for value in changes.values()):
            raise ValueError("Valores nulos não são permitidos.")
        assignments = [f"{key} = ?" for key in changes]
        parameters = [int(value) if key == "completed" else value for key, value in changes.items()]
        assignments.append("updated_at = ?")
        parameters.extend([self._now(), task_id])
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", parameters
                )
                if cursor.rowcount == 0:
                    return None
                row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._as_dict(row)

    def delete(self, task_id: int) -> bool:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0
