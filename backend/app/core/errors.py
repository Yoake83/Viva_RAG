"""Typed application errors. The API layer turns these into a uniform JSON envelope."""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_error"


class ServiceUnavailable(AppError):
    status_code = 503
    code = "service_unavailable"
