# DB models. The constraints that actually matter live here on the tables,
# not just in the API layer, so they hold even if something writes to the DB
# directly.

from datetime import datetime, timezone
from enum import Enum

from sqlmodel import (
    Column,
    DateTime,
    Field,
    Relationship,
    SQLModel,
    UniqueConstraint,
)


def utcnow():
    return datetime.now(timezone.utc)


class DataType(str, Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"


class Dataset(SQLModel, table=True):
    __tablename__ = "datasets"

    id: int | None = Field(default=None, primary_key=True)
    # name is the business identifier -> unique
    name: str = Field(nullable=False, unique=True, index=True, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    data_elements: list["DataElement"] = Relationship(
        back_populates="dataset",
        cascade_delete=True,
    )


class DataElement(SQLModel, table=True):
    __tablename__ = "data_elements"

    # the main business rule: a field name is unique *within* a dataset.
    # Customer.email and Supplier.email are fine, Customer.email twice is not.
    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="uq_element_name_per_dataset"),
    )

    id: int | None = Field(default=None, primary_key=True)
    dataset_id: int = Field(
        foreign_key="datasets.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",  # delete the dataset -> its elements go too
    )
    name: str = Field(nullable=False, max_length=100)
    data_type: DataType = Field(nullable=False)
    description: str | None = Field(default=None, max_length=500)
    is_required: bool = Field(default=False, nullable=False)
    is_pii: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    dataset: Dataset | None = Relationship(back_populates="data_elements")
