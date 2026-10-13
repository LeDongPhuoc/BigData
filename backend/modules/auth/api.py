from fastapi import APIRouter, Request

from backend.core.dependencies import Actor, context
from backend.core.schemas import public
from backend.modules.auth.schemas import Login, Refresh, Register, Tokens
from backend.modules.auth.service import AuthService
from backend.modules.users.schemas import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Tokens, status_code=201)
def register(data: Register, request: Request):
    return AuthService(*context(request)).register(data, request.client.host)


@router.post("/login", response_model=Tokens)
def login(data: Login, request: Request):
    # Ignore forwarded IP headers; trust is configured at the ASGI server boundary.
    return AuthService(*context(request)).login(data, request.client.host)


@router.post("/refresh", response_model=Tokens)
def refresh(data: Refresh, request: Request):
    return AuthService(*context(request)).refresh(data.refresh_token, request.client.host)


@router.post("/logout", status_code=204)
def logout(request: Request, actor: Actor, data: Refresh | None = None):
    AuthService(*context(request)).logout(actor, data.refresh_token if data else None)


@router.get("/me", response_model=User)
def me(actor: Actor):
    return public(actor, omit=("session_id",))
