from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Task(BaseModel):
    title: str
    completed: bool = False

tasks = []


@app.get("/")
def read_root():
    return {"message": "API do Task Manager está viva"}


@app.post("/tasks")
def create_task(task: Task):
    tasks.append(task)
    return task


@app.get("/tasks")
def list_tasks():
    return tasks
