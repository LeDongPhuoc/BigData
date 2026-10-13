from fastapi import APIRouter, Request, Response

from backend.core.dependencies import (
    Actor,
    Idempotency,
    Limit,
    Match,
    Offset,
    context,
    page,
    tagged,
)
from backend.core.schemas import Key, Page
from backend.modules.connections.repository import ConnectionRepository
from backend.modules.connections.schemas import Connection, ConnectionCreate
from backend.modules.connections.service import ConnectionService, view

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("/requests", response_model=Connection, status_code=201)
def create(
    data: ConnectionCreate,
    request: Request,
    response: Response,
    actor: Actor,
    idempotency_key: Idempotency = None,
):
    doc, replay = ConnectionService(*context(request)).create(actor, data, idempotency_key)
    response.status_code = 200 if replay else 201
    tagged(response, doc)
    return view(doc)


@router.get("/requests/incoming", response_model=Page[Connection])
def incoming(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ConnectionRepository(request.app.state.db).inbox(actor["_id"], True, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/requests/outgoing", response_model=Page[Connection])
def outgoing(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ConnectionRepository(request.app.state.db).inbox(actor["_id"], False, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/{connection_id}", response_model=Connection)
def detail(connection_id: Key, request: Request, response: Response, actor: Actor):
    doc = ConnectionService(*context(request)).detail(actor, connection_id)
    tagged(response, doc)
    return view(doc)


@router.post("/{connection_id}/accept", response_model=Connection)
def accept(
    connection_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = ConnectionService(*context(request)).action(actor, connection_id, "accept", if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{connection_id}/reject", response_model=Connection)
def reject(
    connection_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = ConnectionService(*context(request)).action(actor, connection_id, "reject", if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{connection_id}/block", response_model=Connection)
def block(
    connection_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = ConnectionService(*context(request)).action(actor, connection_id, "block", if_match)
    tagged(response, doc)
    return view(doc)


@router.delete("/{connection_id}", status_code=204)
def delete(connection_id: Key, request: Request, actor: Actor, if_match: Match = None):
    ConnectionService(*context(request)).action(actor, connection_id, "delete", if_match)
