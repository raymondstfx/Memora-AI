from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from app.core.auth import get_current_user
from app.schemas.health import ErrorResponse
from app.schemas.presentations import (
    DeckOut,
    DeckRequest,
    SearchRequest,
    WebSearchResult,
)
from app.services.presentations import PresentationService

router = APIRouter(
    prefix="/api",
    tags=["presentations-search"],
    responses={c: {"model": ErrorResponse} for c in (404, 409, 422, 429, 502, 503)},
)
Owner = Annotated[UUID, Depends(get_current_user)]


def service(request: Request) -> PresentationService:
    return cast(PresentationService, request.app.state.presentations)


@router.post("/search", response_model=WebSearchResult)
def search(body: SearchRequest, request: Request, owner: Owner) -> WebSearchResult:
    return service(request).search.search(owner, body.query)


@router.get("/search/config")
def config(request: Request) -> dict[str, object]:
    configured = bool(
        service(request).settings.search_api_key.get_secret_value().strip()
    )
    return {
        "configured": configured,
        "message": "Tavily search ready"
        if configured
        else "Set SEARCH_API_KEY in root backend .env to enable live search.",
    }


@router.post("/presentations/generate", response_model=DeckOut, status_code=202)
@router.post("/presentations", response_model=DeckOut, status_code=202)
def create(body: DeckRequest, request: Request, owner: Owner) -> DeckOut:
    return service(request).create(owner, body)


@router.get("/presentations", response_model=list[DeckOut])
def listing(request: Request, owner: Owner) -> list[DeckOut]:
    return service(request).listing(owner)


@router.get("/presentations/{identifier}", response_model=DeckOut)
def get(identifier: UUID, request: Request, owner: Owner) -> DeckOut:
    return service(request).get(owner, identifier)


@router.post(
    "/presentations/{identifier}/retry", response_model=DeckOut, status_code=202
)
def retry(identifier: UUID, request: Request, owner: Owner) -> DeckOut:
    return service(request).retry(owner, identifier)


@router.get("/presentations/{identifier}/download.{extension}")
def download(
    identifier: UUID, extension: Literal["pptx", "pdf"], request: Request, owner: Owner
) -> FileResponse:
    path = service(request).file(owner, identifier, extension)
    media = (
        "application/pdf"
        if extension == "pdf"
        else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    return FileResponse(
        path,
        media_type=media,
        filename="presentation." + extension,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
        content_disposition_type="inline" if extension == "pdf" else "attachment",
    )


@router.get("/presentations/{identifier}/preview")
def preview(identifier: UUID, request: Request, owner: Owner) -> FileResponse:
    return download(identifier, "pdf", request, owner)


@router.get("/presentations/{identifier}/download")
def editable_download(identifier: UUID, request: Request, owner: Owner) -> FileResponse:
    return download(identifier, "pptx", request, owner)
