"""Public provenance is written by the operator importer, never by client payloads."""

from typing import Annotated

from pydantic import Field

from backend.core.schemas import Schema


class PublicSource(Schema):
    url: str = Field(pattern=r"^https://[A-Za-z0-9.-]+(?:/[^\s]*)?$", max_length=2000)
    publisher: str = Field(min_length=1, max_length=120)
    external_id: str = Field(min_length=1, max_length=200)
    retrieved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
    notes: list[Annotated[str, Field(max_length=500)]] = Field(default_factory=list, max_length=10)
