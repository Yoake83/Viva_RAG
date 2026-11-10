from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.core.errors import AppError
from app.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("viva")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # swap for Alembic migrations before a real deployment
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Viva API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"]
    )

    def envelope(status: int, code: str, message: str, details=None) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return envelope(422, "invalid_request", f"{field or 'Request'}: {first.get('msg', 'invalid value')}")

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("unhandled error")
        return envelope(500, "internal_error", "Something went wrong on the server. Try again.")

    app.include_router(router)
    return app


app = create_app()
