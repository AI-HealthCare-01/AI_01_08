from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel

DocumentStatus = Literal["uploaded", "deleted"]
OcrStatus = Literal["queued", "processing", "success", "failed"]


# 문서 목록 조회 필터 - REQ-DOC-002
class DocumentListQuery(BaseModel):
    patient_id: Annotated[int | None, Field(default=None, ge=1)]
    date_from: date | None = None
    date_to: date | None = None
    document_status: DocumentStatus | None = None
    ocr_status: OcrStatus | None = None


# 대상 patient 귀속 + 업로드/OCR 상태 응답 - REQ-USER-008, REQ-DOC-003
class DocumentUploadResponse(BaseSerializerModel):
    document_id: int
    patient_id: int
    uploaded_by_user_id: int
    status: DocumentStatus
    created_at: datetime


# 문서 목록 조회 응답 - REQ-DOC-002
class DocumentListItemResponse(BaseSerializerModel):
    document_id: int
    patient_id: int
    uploaded_by_user_id: int
    original_filename: str | None
    file_type: str | None
    file_size: int | None
    status: DocumentStatus
    ocr_status: OcrStatus | None
    created_at: datetime


class DocumentListResponse(BaseSerializerModel):
    items: list[DocumentListItemResponse]
    total: int


# 문서 soft delete 응답 - REQ-DOC-001
class DocumentDeleteResponse(BaseSerializerModel):
    document_id: int
    status: Literal["deleted"]
    deleted_at: datetime
