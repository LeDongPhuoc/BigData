import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from arango.exceptions import ArangoClientError, ArangoServerError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.core.config import AppSettings
from backend.core.errors import ApiError
from backend.core.http_limits import RequestLimits
from backend.core.schemas import ErrorEnvelope
from backend.modules.admin.api import router as admin_router
from backend.modules.applications.api import router as applications_router
from backend.modules.audit.api import router as audit_router
from backend.modules.auth.api import router as auth_router
from backend.modules.companies.api import router as companies_router
from backend.modules.connections.api import router as connections_router
from backend.modules.exploration.api import router as exploration_router
from backend.modules.exploration.raw_api import router as raw_exploration_router
from backend.modules.graph.api import router as graph_router
from backend.modules.jobs.api import router as jobs_router
from backend.modules.matching.api import router as matching_router
from backend.modules.notifications.api import router as notifications_router
from backend.modules.profiles.api import router as profiles_router
from backend.modules.referrals.api import router as referrals_router
from backend.modules.skills.api import router as skills_router
from backend.modules.users.api import router as users_router
from database.connection import connect
from database.migrate import validate_schema

logger = logging.getLogger("jrn.http")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


def create_app(config=None, *, db=None):
    config = config or AppSettings.load()
    if db is None and config.database.username == "root":
        raise ValueError("HTTP runtime requires a non-root database account")

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = db if db is not None else connect(config.database)
        validate_schema(app.state.db)  # Startup fails on missing migrations or drift.
        yield

    app = FastAPI(
        title="Job Referral Network API",
        version="0.2.0",
        lifespan=lifespan,
        responses={
            status: {"model": ErrorEnvelope}
            for status in (400, 401, 403, 404, 408, 409, 412, 413, 422, 428, 429, 503)
        },
    )
    app.state.config = config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "If-Match",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["ETag", "X-Request-ID"],
    )
    app.add_middleware(RequestLimits)

    def error_response(request, status, code, message, details=None):
        headers = {"X-Request-ID": getattr(request.state, "request_id", uuid4().hex)}
        if status == 401:
            headers["WWW-Authenticate"] = "Bearer"
        return JSONResponse(
            status_code=status,
            headers=headers,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": headers["X-Request-ID"],
                    "details": details or [],
                }
            },
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request.state.request_id = (
            supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else uuid4().hex
        )
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        route = request.scope.get("route")
        logger.info(
            "request_id=%s method=%s route=%s status=%s duration_ms=%.1f",
            request.state.request_id,
            request.method,
            getattr(route, "path", "unmatched"),
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return error_response(request, error.status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        # Pydantic's input/context/messages can contain passwords or other private input.
        # Return field paths and error types only.
        details = [
            {"field": ".".join(str(p) for p in e["loc"]), "message": e["type"]}
            for e in error.errors()
        ]
        return error_response(request, 422, "validation_error", "Invalid request", details)

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(request, error.status_code, "http_error", "Request unavailable")

    @app.exception_handler(ArangoServerError)
    async def database_error(request, error):
        code = error.error_code
        if code in (1200, 1210):
            return error_response(request, 409, "write_conflict", "Resource conflicts")
        if code == 1202:
            return error_response(request, 404, "not_found", "Resource unavailable")
        if code == 1620:
            return error_response(request, 422, "schema_violation", "Invalid document")
        logger.error("request_id=%s database_code=%s", request.state.request_id, code)
        return error_response(request, 503, "database_unavailable", "Database unavailable")

    @app.exception_handler(ArangoClientError)
    async def connection_error(request, error):
        return error_response(request, 503, "database_unavailable", "Database unavailable")

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        logger.error(
            "request_id=%s exception_type=%s", request.state.request_id, type(error).__name__
        )
        return error_response(request, 500, "internal_error", "Internal error")

    for router in (
        auth_router,
        users_router,
        profiles_router,
        companies_router,
        jobs_router,
        connections_router,
        referrals_router,
        skills_router,
        graph_router,
        matching_router,
        applications_router,
        notifications_router,
        admin_router,
        audit_router,
        exploration_router,
        raw_exploration_router,
    ):
        app.include_router(router, prefix="/api/v1")

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready(request: Request):
        request.app.state.db.version()
        return {"status": "ready"}

    return app
