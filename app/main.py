import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.storage import TaskStore

ROOT = Path(__file__).resolve().parents[1]


class APIModel(BaseModel):
    class Config:
        extra = "forbid"


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    completed: bool = False


class TaskUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None


class TaskRecord(APIModel):
    id: int
    title: str
    completed: bool
    created_at: str
    updated_at: str


def create_app(database_path: str | Path | None = None) -> FastAPI:
    configured_path = database_path or os.getenv(
        "TASK_MANAGER_DB_PATH", str(ROOT / "data" / "tasks.sqlite3")
    )
    store = TaskStore(configured_path)
    application = FastAPI(
        title="Task Manager API",
        description="API para criar, consultar, atualizar e excluir tarefas persistidas em SQLite.",
        version="1.0.0",
    )
    application.state.task_store = store

    @application.get("/", tags=["health"])
    def read_root():
        return {"message": "API do Task Manager está viva"}

    @application.post(
        "/tasks", response_model=TaskRecord, status_code=status.HTTP_201_CREATED, tags=["tasks"]
    )
    def create_task(task: TaskCreate):
        title = task.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="O título não pode estar vazio.")
        return store.create(title=title, completed=task.completed)

    @application.get("/tasks", response_model=list[TaskRecord], tags=["tasks"])
    def list_tasks():
        return store.list()

    @application.get("/tasks/{task_id}", response_model=TaskRecord, tags=["tasks"])
    def get_task(task_id: int):
        task = store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return task

    @application.patch("/tasks/{task_id}", response_model=TaskRecord, tags=["tasks"])
    def update_task(task_id: int, task: TaskUpdate):
        changes = task.dict(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(status_code=422, detail="Informe título ou status válido para atualizar.")
        if "title" in changes:
            changes["title"] = changes["title"].strip()
            if not changes["title"]:
                raise HTTPException(status_code=422, detail="O título não pode estar vazio.")
        updated = store.update(task_id, changes)
        if updated is None:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return updated

    @application.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
    def delete_task(task_id: int):
        if not store.delete(task_id):
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return application


app = create_app()
