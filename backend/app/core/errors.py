from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.schemas.health import ErrorResponse
from app.services.llm.provider import ChatError


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
    @app.exception_handler(ChatError)
    async def chat_error(request: Request, exc: ChatError) -> JSONResponse:
        return error_response(request, exc.status, exc.code, exc.message)

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, exc: IntegrityError) -> JSONResponse:
        return error_response(
            request,
            409,
            "REQUEST_CONFLICT",
            "Request conflicts with an existing operation. "
            "Reload conversation history.",
        )

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
