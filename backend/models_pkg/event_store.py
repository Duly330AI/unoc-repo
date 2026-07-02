from __future__ import annotations

from sqlalchemy import Column as SAColumn
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class EventStoreRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sequence: int = Field(index=True, unique=True)
    event_type: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_column=SAColumn(JSON, nullable=False))
    source: str = Field(default="EVENT_STORE", index=True)
    created_at: str = Field(index=True)
    correlation_id: str | None = Field(default=None, index=True)