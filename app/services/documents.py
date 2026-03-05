import hashlib
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette import status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.documents import (
    DocumentDeleteResponse,
    DocumentListItemResponse,
    DocumentListQuery,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.models.core_auth import UserRole
from app.models.documents import Document, OcrJob
from app.models.patients import CaregiverPatientLink, Patient
from app.models.users import User

ALLOWED_FILE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024


class DocumentService:
    def __init__(self):
        self.upload_root = Path(__file__).resolve().parents[2] / "uploads" / "documents"
        self.upload_root.mkdir(parents=True, exist_ok=True)

    # 대상 patient 귀속 + 업로드/OCR 상태 생성 - REQ-USER-008, REQ-DOC-003
    async def upload_document(self, user: User, file: UploadFile, patient_id: int | None) -> DocumentUploadResponse:
        target_patient = await self._resolve_target_patient_for_upload(user=user, patient_id=patient_id)

        original_filename = Path(file.filename or "").name
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_INPUT")

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_INPUT")
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_INPUT")

        checksum = hashlib.sha256(file_bytes).hexdigest()
        stored_name = f"{datetime.now(config.TIMEZONE).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{extension}"
        stored_path = self.upload_root / stored_name
        stored_path.write_bytes(file_bytes)
        file_url = f"uploads/documents/{stored_name}"

        async with in_transaction() as conn:
            document = await Document.create(
                patient_id=target_patient.id,
                uploaded_by_user_id=user.id,
                file_url=file_url,
                original_filename=original_filename or None,
                file_type=self._normalize_file_type(extension),
                file_size=len(file_bytes),
                checksum=checksum,
                status="uploaded",
                using_db=conn,
            )
            await OcrJob.create(
                document_id=document.id,
                patient_id=target_patient.id,
                status="queued",
                using_db=conn,
            )

        return DocumentUploadResponse(
            document_id=document.id,
            patient_id=document.patient_id,
            uploaded_by_user_id=document.uploaded_by_user_id,
            status=document.status,
            created_at=document.created_at,
        )

    # 문서 목록 조회 및 필터 - REQ-DOC-002
    async def list_documents(self, user: User, query: DocumentListQuery) -> DocumentListResponse:
        accessible_patient_ids = await self._resolve_accessible_patient_ids(user=user, requested_patient_id=query.patient_id)
        if not accessible_patient_ids:
            return DocumentListResponse(items=[], total=0)

        filters: dict[str, object] = {"patient_id__in": accessible_patient_ids}

        # 삭제 문서는 목록에서 제외
        if query.document_status is None:
            filters["status"] = "uploaded"
        elif query.document_status == "deleted":
            return DocumentListResponse(items=[], total=0)
        else:
            filters["status"] = query.document_status

        if query.date_from:
            filters["created_at__gte"] = datetime.combine(query.date_from, time.min, tzinfo=config.TIMEZONE)
        if query.date_to:
            filters["created_at__lt"] = datetime.combine(
                query.date_to + timedelta(days=1), time.min, tzinfo=config.TIMEZONE
            )

        documents = (
            await Document.filter(**filters)
            .select_related("patient", "uploaded_by_user")
            .prefetch_related("ocr_jobs")
            .order_by("-created_at")
        )

        items: list[DocumentListItemResponse] = []
        for document in documents:
            latest_ocr_status = self._get_latest_ocr_status(document=document)
            if query.ocr_status and latest_ocr_status != query.ocr_status:
                continue

            items.append(
                DocumentListItemResponse(
                    document_id=document.id,
                    patient_id=document.patient_id,
                    uploaded_by_user_id=document.uploaded_by_user_id,
                    original_filename=document.original_filename,
                    file_type=document.file_type,
                    file_size=document.file_size,
                    status=document.status,
                    ocr_status=latest_ocr_status,
                    created_at=document.created_at,
                )
            )

        return DocumentListResponse(items=items, total=len(items))

    # 문서 soft delete(권한 검증 포함) - REQ-DOC-001
    async def soft_delete_document(self, user: User, document_id: int) -> DocumentDeleteResponse:
        document = await Document.filter(id=document_id, status="uploaded").select_related("patient").first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if not await self._has_patient_access(user=user, patient_id=document.patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        now = datetime.now(config.TIMEZONE)
        await Document.filter(id=document.id).update(status="deleted", deleted_at=now)

        return DocumentDeleteResponse(
            document_id=document.id,
            status="deleted",
            deleted_at=now,
        )

    # 대상 PATIENT 귀속 검증 - REQ-USER-008, REQ-DOC-003
    async def _resolve_target_patient_for_upload(self, user: User, patient_id: int | None) -> Patient:
        is_patient = await UserRole.filter(user_id=user.id, role__name="PATIENT").exists()
        is_caregiver = await UserRole.filter(user_id=user.id, role__name="CAREGIVER").exists()

        own_patient = await Patient.get_or_none(user_id=user.id)

        if patient_id is None:
            if is_patient and own_patient:
                return own_patient
            if is_caregiver:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_INPUT")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        target_patient = await Patient.get_or_none(id=patient_id)
        if not target_patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if is_patient and own_patient and own_patient.id == patient_id:
            return target_patient

        if is_caregiver and await self._is_active_link(caregiver_user_id=user.id, patient_id=patient_id):
            return target_patient

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

    # 문서 조회 대상 환자 범위 계산 - REQ-DOC-002
    async def _resolve_accessible_patient_ids(self, user: User, requested_patient_id: int | None) -> list[int]:
        is_patient = await UserRole.filter(user_id=user.id, role__name="PATIENT").exists()
        is_caregiver = await UserRole.filter(user_id=user.id, role__name="CAREGIVER").exists()

        own_patient = await Patient.get_or_none(user_id=user.id) if is_patient else None
        own_patient_id = own_patient.id if own_patient else None

        linked_patient_ids: list[int] = []
        if is_caregiver:
            links = await CaregiverPatientLink.filter(
                caregiver_user_id=user.id,
                status="active",
                revoked_at__isnull=True,
            ).values_list("patient_id", flat=True)
            linked_patient_ids = list(links)

        if requested_patient_id is not None:
            if own_patient_id and requested_patient_id == own_patient_id:
                return [requested_patient_id]
            if requested_patient_id in linked_patient_ids:
                return [requested_patient_id]
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        accessible = set(linked_patient_ids)
        if own_patient_id:
            accessible.add(own_patient_id)
        return sorted(accessible)

    # 문서 접근 권한 확인 - REQ-DOC-001, REQ-DOC-002
    async def _has_patient_access(self, user: User, patient_id: int) -> bool:
        own_patient = await Patient.get_or_none(user_id=user.id)
        if own_patient and own_patient.id == patient_id:
            return True
        return await self._is_active_link(caregiver_user_id=user.id, patient_id=patient_id)

    # 보호자-환자 활성 연동 확인 - REQ-USER-008, REQ-DOC-001, REQ-DOC-002
    async def _is_active_link(self, caregiver_user_id: int, patient_id: int) -> bool:
        return await CaregiverPatientLink.filter(
            caregiver_user_id=caregiver_user_id,
            patient_id=patient_id,
            status="active",
            revoked_at__isnull=True,
        ).exists()

    # 업로드 파일 타입 정규화 - REQ-DOC-003
    @staticmethod
    def _normalize_file_type(extension: str) -> str:
        return "pdf" if extension == ".pdf" else "image"

    # 문서별 최신 OCR 상태 계산 - REQ-DOC-002, REQ-DOC-003
    @staticmethod
    def _get_latest_ocr_status(document: Document) -> str | None:
        jobs = list(document.ocr_jobs)
        if not jobs:
            return None
        latest_job = max(jobs, key=lambda job: job.created_at)
        return latest_job.status
