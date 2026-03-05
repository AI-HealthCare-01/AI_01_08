from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.documents import DocumentDeleteResponse, DocumentListQuery, DocumentListResponse, DocumentUploadResponse
from app.models.users import User
from app.services.documents import DocumentService

document_router = APIRouter(prefix="/documents", tags=["documents"])


# 대상 PATIENT 귀속 + 문서 업로드/OCR 작업 생성 - REQ-USER-008, REQ-DOC-003
@document_router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_request_user)],
    document_service: Annotated[DocumentService, Depends(DocumentService)],
    patient_id: Annotated[int | None, Form(ge=1)] = None,
) -> Response:
    result = await document_service.upload_document(user=user, file=file, patient_id=patient_id)
    return Response(result.model_dump(), status_code=status.HTTP_201_CREATED)


# 문서 목록 조회 및 필터 - REQ-DOC-002
@document_router.get("", response_model=DocumentListResponse, status_code=status.HTTP_200_OK)
async def list_documents(
    query: Annotated[DocumentListQuery, Depends()],
    user: Annotated[User, Depends(get_request_user)],
    document_service: Annotated[DocumentService, Depends(DocumentService)],
) -> Response:
    result = await document_service.list_documents(user=user, query=query)
    return Response(result.model_dump(), status_code=status.HTTP_200_OK)


# 문서 soft delete(권한 검증 포함) - REQ-DOC-001
@document_router.delete("/{document_id}", response_model=DocumentDeleteResponse, status_code=status.HTTP_200_OK)
async def soft_delete_document(
    document_id: Annotated[int, Path(ge=1)],
    user: Annotated[User, Depends(get_request_user)],
    document_service: Annotated[DocumentService, Depends(DocumentService)],
) -> Response:
    result = await document_service.soft_delete_document(user=user, document_id=document_id)
    return Response(result.model_dump(), status_code=status.HTTP_200_OK)
