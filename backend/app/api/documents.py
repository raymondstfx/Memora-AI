from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.auth import get_current_user
from app.schemas.documents import (
    DocumentConfiguration,
    DocumentOut,
    JobOut,
    ReprocessRequest,
    SearchRequest,
    SearchResult,
    UploadResult,
)
from app.schemas.health import ErrorResponse
from app.services.documents import DocumentService
from app.services.embedding import embedding_configuration
from app.services.llm.provider import ChatError

router = APIRouter(
    prefix="/api",
    tags=["documents"],
    responses={
        code: {"model": ErrorResponse} for code in (404, 409, 413, 415, 422, 429, 503)
    },
)
Owner = Annotated[UUID, Depends(get_current_user)]


def service(request: Request) -> DocumentService:
    return cast(DocumentService, request.app.state.documents)


@router.get("/documents/config", response_model=DocumentConfiguration)
def config(request: Request) -> DocumentConfiguration:
    return embedding_configuration(service(request).settings)


@router.post("/documents/upload", status_code=202, response_model=UploadResult)
async def upload(
    request: Request, owner: Owner, file: Annotated[UploadFile, File()]
) -> UploadResult:
    documents = service(request)
    try:
        content = await file.read(documents.settings.pdf_max_upload_bytes + 1)
        return await run_in_threadpool(
            documents.upload,
            owner,
            file.filename or "",
            file.content_type or "",
            content,
        )
    finally:
        await file.close()


@router.get("/documents", response_model=list[DocumentOut])
def listing(request: Request, owner: Owner) -> list[DocumentOut]:
    return service(request).listing(owner)


@router.post("/documents/search", response_model=SearchResult)
def search(body: SearchRequest, request: Request, owner: Owner) -> SearchResult:
    sources = service(request).retrieve(owner, body.question, body.document_ids)
    return SearchResult(
        sources=sources,
        message="Evidence retrieved."
        if sources
        else "No supporting PDF evidence found.",
    )


@router.get("/documents/{identifier}", response_model=DocumentOut)
def detail(identifier: UUID, request: Request, owner: Owner) -> DocumentOut:
    return service(request).detail(owner, identifier)


@router.get("/documents/{identifier}/file")
def original(identifier: UUID, request: Request, owner: Owner) -> FileResponse:
    documents = service(request)
    with documents.sessions() as db:
        row = documents.owned(db, owner, identifier)
        path = documents.storage.path(row.storage_key)
        if not path.is_file():
            raise ChatError("PDF_STORAGE_MISSING", "Stored PDF is missing.", 404)
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=row.filename,
            content_disposition_type="inline",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox",
            },
        )


@router.post(
    "/documents/{identifier}/retry", status_code=202, response_model=UploadResult
)
def retry(
    identifier: UUID, body: ReprocessRequest, request: Request, owner: Owner
) -> UploadResult:
    return service(request).reprocess(owner, identifier, False, body.reparse)


@router.post(
    "/documents/{identifier}/reindex", status_code=202, response_model=UploadResult
)
def reindex(
    identifier: UUID, body: ReprocessRequest, request: Request, owner: Owner
) -> UploadResult:
    return service(request).reprocess(owner, identifier, True, body.reparse)


@router.delete("/documents/{identifier}", status_code=204)
def remove(identifier: UUID, request: Request, owner: Owner) -> Response:
    service(request).remove(owner, identifier)
    return Response(status_code=204)


@router.get("/jobs/{identifier}", response_model=JobOut)
def job(identifier: UUID, request: Request, owner: Owner) -> JobOut:
    return service(request).job(owner, identifier)
