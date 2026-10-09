"""Request and response models for the Task Manager API."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    completed: bool = False

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("O título não pode estar vazio.")
        return title


class TaskUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return TaskCreate.normalize_title(value) if value is not None else None

    @model_validator(mode="after")
    def require_changes(self) -> "TaskUpdate":
        changes = self.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise ValueError("Informe título ou status válido para atualizar.")
        return self


class TaskRecord(APIModel):
    id: int
    title: str
    completed: bool
    created_at: str
    updated_at: str
