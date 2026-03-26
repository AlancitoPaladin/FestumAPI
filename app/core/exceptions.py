from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    status_code = 400
    message: str | None = None
    detail = "API error"
    code: str | None = None

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        if detail:
            self.detail = detail
        if code:
            self.code = code
        if message:
            self.message = message


class ResourceNotFoundError(ApiError):
    status_code = 404
    detail = "Resource not found"
    code = "NOT_FOUND"


class ResourceConflictError(ApiError):
    status_code = 409
    detail = "Resource conflict"


class UnauthorizedError(ApiError):
    status_code = 401
    detail = "Unauthorized"
    code = "UNAUTHORIZED"


class ForbiddenError(ApiError):
    status_code = 403
    detail = "Forbidden"
    code = "FORBIDDEN"


class ServiceUnavailableError(ApiError):
    status_code = 503
    detail = "Service temporarily unavailable"
    code = "SERVICE_UNAVAILABLE"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation failed",
                "detail": str(exc.errors()),
                "code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        payload = {
            "success": False,
            "message": exc.message or exc.detail,
            "detail": exc.detail,
            "code": exc.code or "API_ERROR",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
        )
