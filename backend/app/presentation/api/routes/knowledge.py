import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.app.application.rag.document_catalog_service import DocumentCatalogService
from backend.app.application.rag.document_ingestion_service import DocumentIngestionService
from backend.app.application.rag.rag_service import RAGService
from backend.app.core.settings import Settings
from backend.app.presentation.api.dependencies.providers import (
    DEFAULT_KNOWLEDGE_COLLECTION,
    get_app_settings,
    get_document_catalog_service,
    get_document_ingestion_service,
    get_rag_service,
)
from backend.app.presentation.api.dependencies.security import (
    SecurityRole,
    require_minimum_role,
)
from backend.app.presentation.api.schemas.common import DeleteResponse
from backend.app.presentation.api.schemas.knowledge import (
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
)


router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])

UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
SUPPORTED_UPLOAD_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".markdown"}


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传知识库文档",
    description="将 PDF、DOCX、TXT 或 Markdown 文档上传到知识库。",
    dependencies=[Depends(require_minimum_role(SecurityRole.ANALYST))],
)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Form(DEFAULT_KNOWLEDGE_COLLECTION),
    domain: str = Form("general"),
    tags: str = Form(""),
    settings: Settings = Depends(get_app_settings),
    ingestion_service: DocumentIngestionService = Depends(get_document_ingestion_service),
    catalog: DocumentCatalogService = Depends(get_document_catalog_service),
) -> DocumentUploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    settings.paths.temp_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="upload-", dir=settings.paths.temp_dir))
    temp_path = temp_dir / Path(file.filename or f"upload{suffix}").name
    try:
        await _stage_upload(file, temp_path)
        result = await ingestion_service.ingest_file(
            temp_path,
            collection_name=collection_name,
            domain=domain,
            tags=_parse_tags(tags),
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    catalog.register(result)
    return DocumentUploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        file_type=result.file_type,
        domain=result.domain,
        collection_name=result.collection_name,
        chunk_count=result.chunk_count,
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="查看知识库文档",
)
def list_documents(
    catalog: DocumentCatalogService = Depends(get_document_catalog_service),
) -> DocumentListResponse:
    return DocumentListResponse(
        documents=[
            DocumentSummary(
                document_id=document.document_id,
                filename=document.filename,
                file_type=document.file_type,
                domain=document.domain,
                collection_name=document.collection_name,
                chunk_count=document.chunk_count,
            )
            for document in catalog.list()
        ]
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    summary="删除知识库文档",
    dependencies=[Depends(require_minimum_role(SecurityRole.ANALYST))],
)
def delete_document(
    document_id: str,
    catalog: DocumentCatalogService = Depends(get_document_catalog_service),
) -> DeleteResponse:
    if not catalog.delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return DeleteResponse(deleted=True, document_id=document_id)


@router.post(
    "/query",
    response_model=KnowledgeQueryResponse,
    summary="查询知识库",
    description="执行 RAG 检索并生成有依据的回答。",
)
async def query_knowledge(
    request: KnowledgeQueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> KnowledgeQueryResponse:
    kwargs = {
        "collection_name": request.collection_name,
        "top_k": request.top_k,
        "metadata_filter": request.metadata_filter,
        "score_threshold": request.score_threshold,
        "retrieval_mode": request.retrieval_mode,
    }
    try:
        response = await rag_service.answer(request.question, **kwargs)
    except TypeError as exc:
        if "unexpected keyword argument 'retrieval_mode'" not in str(exc):
            raise
        kwargs.pop("retrieval_mode")
        response = await rag_service.answer(request.question, **kwargs)
    return KnowledgeQueryResponse(
        answer=response.answer,
        citations=response.citations,
        metadata=response.metadata,
        token_usage=response.token_usage,
    )


async def _stage_upload(file: UploadFile, destination: Path) -> int:
    """Stream an uploaded file to a project-local staging path with hard bounds."""

    bytes_written = 0
    with destination.open("wb") as output:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MiB limit",
                )
            output.write(chunk)

    if bytes_written == 0:
        raise HTTPException(status_code=400, detail="Empty file is not allowed")
    return bytes_written


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]
