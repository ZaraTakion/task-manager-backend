"""HTTP entry point. API contracts remain compatible with version 1.0."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response, Security, status
from fastapi import Path as APIPath
from fastapi.security import APIKeyHeader

from app.schemas import TaskCreate, TaskRecord, TaskUpdate
from app.storage import TaskRow, TaskStore

ROOT = Path(__file__).resolve().parents[1]


def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Build an independent application with its own SQLite database."""
    configured_path = (
        database_path
        if database_path is not None
        else os.getenv("TASK_MANAGER_DB_PATH", str(ROOT / "data" / "tasks.sqlite3"))
    )
    store = TaskStore(configured_path)
    api_key = os.getenv("TASK_MANAGER_API_KEY")
    if api_key is not None and not api_key.strip():
        raise ValueError("TASK_MANAGER_API_KEY não pode ser vazio.")

    application = FastAPI(
        title="Task Manager API",
        description="API para criar, consultar, atualizar e excluir tarefas persistidas em SQLite.",
        version="1.1.0",
    )
    application.state.task_store = store

    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    def check_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
        if api_key is not None and (
            x_api_key is None or not secrets.compare_digest(x_api_key, api_key)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Chave de API inválida ou ausente.",
                headers={"WWW-Authenticate": "APIKey"},
            )

    task_dependencies = [Depends(check_api_key)]

    @application.get("/", tags=["health"])
    def read_root() -> dict[str, str]:
        return {"message": "API do Task Manager está viva"}

    @application.post(
        "/tasks",
        response_model=TaskRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["tasks"],
        dependencies=task_dependencies,
    )
    def create_task(task: TaskCreate) -> TaskRow:
        return store.create(title=task.title, completed=task.completed)

    @application.get(
        "/tasks", response_model=list[TaskRecord], tags=["tasks"], dependencies=task_dependencies
    )
    def list_tasks(
        completed: bool | None = Query(default=None),
        limit: int | None = Query(default=None, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> list[TaskRow]:
        return store.list(completed=completed, limit=limit, offset=offset)

    @application.get(
        "/tasks/{task_id}",
        response_model=TaskRecord,
        tags=["tasks"],
        dependencies=task_dependencies,
    )
    def get_task(task_id: int = APIPath(gt=0)) -> TaskRow:
        task = store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return task

    @application.patch(
        "/tasks/{task_id}",
        response_model=TaskRecord,
        tags=["tasks"],
        dependencies=task_dependencies,
    )
    def update_task(task: TaskUpdate, task_id: int = APIPath(gt=0)) -> TaskRow:
        updated = store.update(task_id, task.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return updated

    @application.delete(
        "/tasks/{task_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["tasks"],
        dependencies=task_dependencies,
    )
    def delete_task(task_id: int = APIPath(gt=0)) -> Response:
        if not store.delete(task_id):
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return application


app = create_app()
