from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.health import ErrorResponse


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    body = ErrorResponse(
        code=code, message=message, request_id=request_id, details=details
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(exclude_none=True),
        headers={"X-Request-ID": request_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(request, exc.status_code, "HTTP_ERROR", "Request failed.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            request, 422, "VALIDATION_ERROR", "Request validation failed."
        )
