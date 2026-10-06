# Request/response models. Kept separate from the table models so clients
# can't set things like id or created_at, and so the API shape and the stored
# shape can change independently.

from datetime import datetime

from pydantic import field_validator
from sqlmodel import SQLModel

from .models import DataType


class DatasetCreate(SQLModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def no_blank_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class DataElementRead(SQLModel):
    id: int
    dataset_id: int
    name: str
    data_type: DataType
    description: str | None
    is_required: bool
    is_pii: bool
    created_at: datetime


class DatasetRead(SQLModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class DatasetReadWithElements(DatasetRead):
    data_elements: list[DataElementRead] = []


class DataElementCreate(SQLModel):
    name: str
    data_type: DataType
    description: str | None = None
    is_required: bool = False
    is_pii: bool = False

    @field_validator("name")
    @classmethod
    def no_blank_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v
