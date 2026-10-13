from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

Key = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
Timestamp = str
T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Page(Schema, Generic[T]):
    items: list[T]
    offset: int
    limit: int
    has_more: bool


class Action(Schema):
    reason: str | None = Field(default=None, max_length=500)


class Revisioned(Schema):
    id: Key
    revision: str
    created_at: Timestamp
    updated_at: Timestamp


class ErrorDetail(Schema):
    field: str
    message: str


class ErrorBody(Schema):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail]


class ErrorEnvelope(Schema):
    error: ErrorBody


def public(doc, *, omit=()):
    return {
        **{k: v for k, v in doc.items() if not k.startswith("_") and k not in omit},
        "id": doc["_key"],
        "revision": doc["_rev"],
    }


def key(document_id: str | None):
    return document_id.split("/", 1)[-1] if document_id else None
