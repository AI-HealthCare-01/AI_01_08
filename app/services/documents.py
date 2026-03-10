import asyncio
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette import status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.documents import (
    DocumentDeleteResponse,
    DocumentDrugPatchItemRequest,
    DocumentDrugPatchRequest,
    DocumentDrugPatchResponse,
    DocumentDrugsResponse,
    DocumentListItemResponse,
    DocumentListQuery,
    DocumentListResponse,
    DocumentOcrStatusResponse,
    DocumentUploadResponse,
    ExtractedDrugItemResponse,
    ExtractedDrugMfdsInfoResponse,
    ExtractedDrugValidationResponse,
)
from app.models.documents import Document, ExtractedMed, OcrJob
from app.models.healthcare import UserRole
from app.models.medications import DrugInfoCache, PatientMed
from app.models.patients import CaregiverPatientLink, Patient
from app.models.users import User
from app.services.mfds import MfdsService
from app.services.ocr import OcrService

ALLOWED_FILE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
DRUG_FORM_SUFFIXES = ("장용캡슐", "연질캡슐", "서방정", "캡슐", "정", "액", "주", "겔", "시럽", "크림", "로션")


@dataclass(frozen=True)
class DrugCacheResolution:
    cache: DrugInfoCache | None
    name_match_status: str


class DocumentService:
    def __init__(self):
        self.upload_root = Path(__file__).resolve().parents[2] / "uploads" / "documents"
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.ocr_service = OcrService()
        self.mfds_service = MfdsService()

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
            ocr_job = await OcrJob.create(
                document_id=document.id,
                patient_id=target_patient.id,
                status="queued",
                using_db=conn,
            )

        # REQ-DOC-003 - 업로드 직후 OCR 비동기 처리 시작
        asyncio.create_task(self.ocr_service.process_ocr_job(ocr_job_id=ocr_job.id))

        return DocumentUploadResponse(
            document_id=document.id,
            patient_id=document.patient_id,
            uploaded_by_user_id=document.uploaded_by_user_id,
            status=document.status,
            created_at=document.created_at,
        )

    # 문서 목록 조회 및 필터 - REQ-DOC-002
    async def list_documents(self, user: User, query: DocumentListQuery) -> DocumentListResponse:
        accessible_patient_ids = await self._resolve_accessible_patient_ids(
            user=user, requested_patient_id=query.patient_id
        )
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

    # OCR 처리 상태 조회(권한 검증 포함) - REQ-DOC-003
    async def get_document_ocr_status(self, user: User, document_id: int) -> DocumentOcrStatusResponse:
        document = await Document.filter(id=document_id).prefetch_related("ocr_jobs").first()
        if not document or document.status == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if not await self._has_patient_access(user=user, patient_id=document.patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        latest_job = self._get_latest_ocr_job(document=document)

        return DocumentOcrStatusResponse(
            document_id=document.id,
            patient_id=document.patient_id,
            document_status=document.status,
            ocr_job_id=latest_job.id if latest_job else None,
            ocr_status=latest_job.status if latest_job else None,
            retry_count=latest_job.retry_count if latest_job else None,
            error_code=latest_job.error_code if latest_job else None,
            error_message=latest_job.error_message if latest_job else None,
            created_at=latest_job.created_at if latest_job else document.created_at,
            updated_at=latest_job.updated_at if latest_job else None,
        )

    # 추출 약 목록 조회(권한 검증 포함) - REQ-DOC-006
    async def get_document_drugs(
        self, user: User, document_id: int, include_mfds: bool = True
    ) -> DocumentDrugsResponse:
        document = await Document.get_or_none(id=document_id)
        if not document or document.status == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if not await self._has_patient_access(user=user, patient_id=document.patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        latest_job = await OcrJob.filter(document_id=document.id).order_by("-created_at").first()
        if not latest_job or latest_job.status != "success":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNPROCESSABLE")

        extracted_meds = await ExtractedMed.filter(ocr_job_id=latest_job.id).order_by("id")
        if not extracted_meds:
            # REQ-DOC-005, REQ-DOC-006 - 과거 OCR 성공건의 raw_text 기반 추출 결과 백필
            backfilled_count = await self.ocr_service.backfill_extracted_meds(ocr_job_id=latest_job.id)
            if backfilled_count > 0:
                extracted_meds = await ExtractedMed.filter(ocr_job_id=latest_job.id).order_by("id")

        response_items = await self._build_extracted_drug_items(
            extracted_meds=extracted_meds, fetch_missing=include_mfds
        )

        return DocumentDrugsResponse(
            document_id=document.id,
            patient_id=document.patient_id,
            ocr_job_id=latest_job.id,
            ocr_status=latest_job.status,
            items=response_items,
            total=len(response_items),
        )

    # 추출 약 수정/확정(권한 검증 포함) - REQ-DOC-007
    async def patch_document_drugs(
        self, user: User, document_id: int, payload: DocumentDrugPatchRequest
    ) -> DocumentDrugPatchResponse:
        document = await Document.get_or_none(id=document_id)
        if not document or document.status == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if not await self._has_patient_access(user=user, patient_id=document.patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        latest_job = await OcrJob.filter(document_id=document.id).order_by("-created_at").first()
        if not latest_job or latest_job.status != "success":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNPROCESSABLE")

        async with in_transaction() as conn:
            existing_meds = await ExtractedMed.filter(ocr_job_id=latest_job.id).using_db(conn)
            existing_by_id = {med.id: med for med in existing_meds}
            touched_med_ids: list[int] = []

            for item in payload.items:
                if item.extracted_med_id is not None:
                    target_med = existing_by_id.get(item.extracted_med_id)
                    if not target_med:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

                    await (
                        ExtractedMed.filter(id=target_med.id)
                        .using_db(conn)
                        .update(
                            name=item.name.strip(),
                            dosage_text=self._nullable_str(item.dosage_text),
                            frequency_text=self._nullable_str(item.frequency_text),
                            duration_text=self._nullable_str(item.duration_text),
                            confidence=item.confidence,
                        )
                    )
                    touched_med_ids.append(target_med.id)
                    continue

                created_med = await self._create_extracted_med_from_patch_item(
                    item=item,
                    ocr_job_id=latest_job.id,
                    patient_id=document.patient_id,
                    using_db=conn,
                )
                touched_med_ids.append(created_med.id)

            if payload.replace_all:
                delete_query = ExtractedMed.filter(ocr_job_id=latest_job.id).using_db(conn)
                if touched_med_ids:
                    delete_query = delete_query.exclude(id__in=touched_med_ids)
                await delete_query.delete()

            updated_meds = await ExtractedMed.filter(ocr_job_id=latest_job.id).using_db(conn).order_by("id")

            confirmed_patient_med_count = 0
            if payload.confirm:
                confirmed_patient_med_count = await self._sync_confirmed_meds(
                    document=document,
                    ocr_job=latest_job,
                    extracted_meds=updated_meds,
                    using_db=conn,
                )

        response_items = await self._build_extracted_drug_items(extracted_meds=updated_meds, fetch_missing=True)
        return DocumentDrugPatchResponse(
            document_id=document.id,
            patient_id=document.patient_id,
            ocr_job_id=latest_job.id,
            confirmed=payload.confirm,
            updated_count=len(response_items),
            confirmed_patient_med_count=confirmed_patient_med_count,
            items=response_items,
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
        latest_job = DocumentService._get_latest_ocr_job(document=document)
        return latest_job.status if latest_job else None

    # 문서별 최신 OCR Job 계산 - REQ-DOC-003
    @staticmethod
    def _get_latest_ocr_job(document: Document) -> OcrJob | None:
        jobs = list(document.ocr_jobs)
        if not jobs:
            return None
        return max(jobs, key=lambda job: job.created_at)

    # 추출 약 응답 변환 - REQ-DOC-006, REQ-DOC-007
    @staticmethod
    def _to_extracted_drug_item_response(
        med: ExtractedMed,
        validation: ExtractedDrugValidationResponse,
        mfds_info: ExtractedDrugMfdsInfoResponse | None = None,
    ) -> ExtractedDrugItemResponse:
        return ExtractedDrugItemResponse(
            extracted_med_id=med.id,
            ocr_job_id=med.ocr_job_id,
            patient_id=med.patient_id,
            name=med.name,
            dosage_text=med.dosage_text,
            frequency_text=med.frequency_text,
            duration_text=med.duration_text,
            confidence=float(med.confidence) if med.confidence is not None else None,
            mfds_info=mfds_info,
            validation=validation,
            created_at=med.created_at,
        )

    # 추출 약 신규 생성 - REQ-DOC-007
    async def _create_extracted_med_from_patch_item(
        self,
        item: DocumentDrugPatchItemRequest,
        ocr_job_id: int,
        patient_id: int,
        using_db,
    ) -> ExtractedMed:
        return await ExtractedMed.create(
            ocr_job_id=ocr_job_id,
            patient_id=patient_id,
            name=item.name.strip(),
            dosage_text=self._nullable_str(item.dosage_text),
            frequency_text=self._nullable_str(item.frequency_text),
            duration_text=self._nullable_str(item.duration_text),
            confidence=item.confidence,
            using_db=using_db,
        )

    # 추출 약 확정 시 patient_meds 동기화 - REQ-DOC-007
    async def _sync_confirmed_meds(
        self, document: Document, ocr_job: OcrJob, extracted_meds: list[ExtractedMed], using_db
    ) -> int:
        now = datetime.now(config.TIMEZONE)

        await (
            PatientMed.filter(
                patient_id=document.patient_id,
                source_document_id=document.id,
                is_active=True,
            )
            .using_db(using_db)
            .update(is_active=False)
        )

        created_count = 0
        for med in extracted_meds:
            matched_cache_resolution = await self._resolve_drug_cache(name=med.name, fetch_missing=True)
            matched_cache = matched_cache_resolution.cache
            await PatientMed.create(
                patient_id=document.patient_id,
                source_document_id=document.id,
                source_ocr_job_id=ocr_job.id,
                source_extracted_med_id=med.id,
                drug_info_cache_id=matched_cache.id if matched_cache else None,
                display_name=med.name,
                dosage=med.dosage_text,
                route=None,
                notes="confirmed_from_ocr",
                is_active=True,
                confirmed_at=now,
                using_db=using_db,
            )
            created_count += 1
        return created_count

    # 입력 문자열 정규화 - REQ-DOC-007
    @staticmethod
    def _nullable_str(value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    # 추출 약 목록 응답 조립 - REQ-DOC-006, REQ-DOC-007, REQ-DRUG-001, REQ-DRUG-005
    async def _build_extracted_drug_items(
        self, extracted_meds: list[ExtractedMed], fetch_missing: bool
    ) -> list[ExtractedDrugItemResponse]:
        response_items: list[ExtractedDrugItemResponse] = []
        for med in extracted_meds:
            cache_resolution = await self._resolve_drug_cache(name=med.name, fetch_missing=fetch_missing)
            cache = cache_resolution.cache
            mfds_info = (
                ExtractedDrugMfdsInfoResponse(
                    drug_info_cache_id=cache.id,
                    mfds_item_seq=cache.mfds_item_seq,
                    drug_name_display=cache.drug_name_display,
                    manufacturer=cache.manufacturer,
                    efficacy=cache.efficacy,
                    dosage_info=cache.dosage_info,
                    precautions=cache.precautions,
                    storage_method=cache.storage_method,
                    expires_at=cache.expires_at,
                )
                if cache
                else None
            )

            validation = self._build_validation_status(med=med, cache_resolution=cache_resolution)
            response_items.append(
                self._to_extracted_drug_item_response(med=med, validation=validation, mfds_info=mfds_info)
            )
        return response_items

    # 자동 검증 상태 계산 - REQ-DRUG-001, REQ-DRUG-005
    def _build_validation_status(
        self, med: ExtractedMed, cache_resolution: DrugCacheResolution
    ) -> ExtractedDrugValidationResponse:
        dosage_check_status = self._evaluate_dosage_check_status(med=med, cache=cache_resolution.cache)
        needs_review = cache_resolution.name_match_status != "exact" or dosage_check_status in {"missing", "mismatch"}

        reason = None
        if cache_resolution.name_match_status == "unmatched":
            reason = "약명 매칭 실패"
        elif dosage_check_status == "mismatch":
            reason = "용량 정보 불일치 가능성"
        elif dosage_check_status == "missing":
            reason = "용량 정보 누락"

        return ExtractedDrugValidationResponse(
            name_match_status=cache_resolution.name_match_status,  # type: ignore[arg-type]
            dosage_check_status=dosage_check_status,  # type: ignore[arg-type]
            needs_review=needs_review,
            reason=reason,
        )

    # 용량 검증 상태 계산 - REQ-DRUG-002, REQ-DRUG-005
    def _evaluate_dosage_check_status(self, med: ExtractedMed, cache: DrugInfoCache | None) -> str:
        if not med.dosage_text:
            return "missing"
        if not cache or not cache.dosage_info:
            return "unknown"

        normalized_dosage_text = self._normalize_mfds_keyword(value=med.dosage_text)
        normalized_dosage_info = self._normalize_mfds_keyword(value=cache.dosage_info)
        if normalized_dosage_text and normalized_dosage_text in normalized_dosage_info:
            return "ok"
        return "mismatch"

    # 약명 기준 drug_info_cache 조회/동기화 - REQ-DRUG-001, REQ-DRUG-002, REQ-DRUG-003
    async def _resolve_drug_cache(self, name: str, fetch_missing: bool) -> DrugCacheResolution:
        keyword = self._normalize_mfds_keyword(value=name)
        if not keyword:
            return DrugCacheResolution(cache=None, name_match_status="unmatched")

        matched_cache, name_match_status = await self._find_best_drug_cache(keyword=keyword)
        if matched_cache or not fetch_missing or not config.MFDS_SERVICE_KEY:
            return DrugCacheResolution(cache=matched_cache, name_match_status=name_match_status)

        try:
            await self.mfds_service.search_easy_drug_info(drug_name=keyword, num_of_rows=5)
        except HTTPException:
            return DrugCacheResolution(cache=None, name_match_status="unmatched")

        matched_cache, name_match_status = await self._find_best_drug_cache(keyword=keyword)
        return DrugCacheResolution(cache=matched_cache, name_match_status=name_match_status)

    # 약명 기반 캐시 후보 조회(부분 일치 + 형태소 suffix 제거 fallback) - REQ-DRUG-001, REQ-DRUG-005
    async def _find_best_drug_cache(self, keyword: str) -> tuple[DrugInfoCache | None, str]:  # noqa: C901
        candidates = await DrugInfoCache.filter(drug_name_display__contains=keyword).order_by("-updated_at").limit(10)
        if not candidates:
            stripped_keyword = self._strip_drug_form_suffix(keyword=keyword)
            if stripped_keyword and stripped_keyword != keyword:
                candidates = (
                    await DrugInfoCache.filter(drug_name_display__contains=stripped_keyword)
                    .order_by("-updated_at")
                    .limit(10)
                )
                keyword = stripped_keyword
        if not candidates:
            return None, "unmatched"

        normalized_keyword = self._normalize_mfds_keyword(value=keyword)

        def score(cache: DrugInfoCache) -> tuple[int, int]:
            normalized_display_name = self._normalize_mfds_keyword(value=cache.drug_name_display or "")
            if not normalized_display_name:
                return (0, 0)
            if normalized_display_name == normalized_keyword:
                return (3, len(normalized_display_name))
            if normalized_keyword in normalized_display_name:
                return (2, len(normalized_display_name))
            if normalized_display_name in normalized_keyword:
                return (1, len(normalized_display_name))
            return (0, len(normalized_display_name))

        best_cache = max(candidates, key=score)
        best_score = score(best_cache)[0]
        if best_score == 3:
            return best_cache, "exact"
        if best_score in {1, 2}:
            return best_cache, "candidate"
        return best_cache, "unmatched"

    # MFDS 조회 키워드 정규화 - REQ-DRUG-005
    @staticmethod
    def _normalize_mfds_keyword(value: str) -> str:
        normalized_value = value.strip()
        normalized_value = normalized_value.replace("캅셀", "캡슐").replace("캡셀", "캡슐").replace("캅슐", "캡슐")
        normalized_value = re.sub(r"\s+", "", normalized_value)
        normalized_value = re.sub(r"[^A-Za-z가-힣0-9]", "", normalized_value)
        return normalized_value

    # 약 제형 suffix 제거 - REQ-DRUG-005
    @staticmethod
    def _strip_drug_form_suffix(keyword: str) -> str:
        for suffix in DRUG_FORM_SUFFIXES:
            if keyword.endswith(suffix) and len(keyword) > len(suffix) + 1:
                return keyword[: -len(suffix)]
        return keyword
