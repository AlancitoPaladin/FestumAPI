from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    status_code = 400
    detail = "API error"

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail


class ResourceNotFoundError(ApiError):
    status_code = 404
    detail = "Resource not found"


class ResourceConflictError(ApiError):
    status_code = 409
    detail = "Resource conflict"


class UnauthorizedError(ApiError):
    status_code = 401
    detail = "Unauthorized"


class ForbiddenError(ApiError):
    status_code = 403
    detail = "Forbidden"


class ServiceUnavailableError(ApiError):
    status_code = 503
    detail = "Service temporarily unavailable"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.detail},
        )
