import asyncio
import base64
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import HTTPException
from starlette import status

from app.core import config
from app.dtos.documents import DocumentOcrRetryResponse
from app.models.documents import Document, ExtractedMed, OcrJob, OcrRawText
from app.models.patients import CaregiverPatientLink, Patient
from app.models.users import User
from app.services.barcode import BarcodeService

MED_NAME_SUFFIX_PATTERN = (
    "연질캡슐|장용캡슐|서방정|캅셀|캡셀|캅슐|캡슐|시럽|현탁액|주사액|크림|로션|패취|패치|정|산|주|액|겔"
)
KOREAN_MED_NAME_PATTERN = re.compile(rf"([A-Za-z가-힣0-9+\-/]{{2,}}(?:{MED_NAME_SUFFIX_PATTERN}))")
ENGLISH_MED_WITH_DOSE_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9+\-/]{2,})\b\s*(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL))",
    re.IGNORECASE,
)
DOSAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL|정|캡슐|T))\b", re.IGNORECASE)
FREQUENCY_PATTERN = re.compile(
    r"(1일\s*\d+\s*회|하루\s*\d+\s*회|매일\s*\d+\s*회|\d+\s*회|아침|점심|저녁|취침\s*전|필요\s*시|PRN)",
    re.IGNORECASE,
)
DURATION_PATTERN = re.compile(r"(\d+\s*(?:일분|일|주|개월)(?:간)?)")
COUNT_DOSAGE_PATTERN = re.compile(r"(\d+(?:\.\d+)?\s*(?:(?:정|캡슐|알|포)(?:씩)?|T))")
NOISE_KEYWORDS = {
    "환자정보",
    "병원정보",
    "복약안내",
    "조제약사",
    "조제일자",
    "사업자등록번호",
    "전화",
    "처방전",
    "약국",
    "보험",
    "수납",
    "금액",
}
GENERIC_MED_NAMES = {
    "필름코팅정",
    "변형정",
    "장용정",
    "서방정",
    "연질캡슐",
    "장용캡슐",
    "캡슐",
    "정",
    "주",
    "액",
    "겔",
    "시럽",
    "크림",
    "로션",
}


class OcrService:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.barcode_service = BarcodeService()

    # REQ-DOC-008 - OCR 재시도 요청 처리
    async def retry_document_ocr(self, user: User, document_id: int) -> DocumentOcrRetryResponse:
        document = await Document.filter(id=document_id, status="uploaded").first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

        if not await self._has_patient_access(user=user, patient_id=document.patient_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")

        latest_job = await OcrJob.filter(document_id=document.id).order_by("-created_at").first()
        if latest_job and latest_job.status == "processing":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNPROCESSABLE")
        if latest_job and latest_job.status == "queued":
            # REQ-DOC-008 - 대기중 job이 남아있으면 해당 job을 재실행 트리거
            asyncio.create_task(self.process_ocr_job(ocr_job_id=latest_job.id))
            return DocumentOcrRetryResponse(
                document_id=document.id,
                ocr_job_id=latest_job.id,
                status=latest_job.status,
                retry_count=latest_job.retry_count,
                queued_at=latest_job.created_at,
            )

        next_retry_count = (latest_job.retry_count + 1) if latest_job else 0
        ocr_job = await OcrJob.create(
            document_id=document.id,
            patient_id=document.patient_id,
            status="queued",
            retry_count=next_retry_count,
            error_code=None,
            error_message=None,
        )

        # REQ-DOC-003 - 비동기 OCR 실행 트리거
        asyncio.create_task(self.process_ocr_job(ocr_job_id=ocr_job.id))

        return DocumentOcrRetryResponse(
            document_id=document.id,
            ocr_job_id=ocr_job.id,
            status=ocr_job.status,
            retry_count=ocr_job.retry_count,
            queued_at=ocr_job.created_at,
        )

    # REQ-DOC-005 - 기존 성공 OCR job 원문으로 추출 약 데이터 백필
    async def backfill_extracted_meds(self, ocr_job_id: int) -> int:
        ocr_job = await OcrJob.get_or_none(id=ocr_job_id)
        if not ocr_job:
            return 0

        raw_text_row = await OcrRawText.get_or_none(ocr_job_id=ocr_job_id)
        if not raw_text_row or not raw_text_row.raw_text.strip():
            await ExtractedMed.filter(ocr_job_id=ocr_job_id).delete()
            return 0

        await self._save_extracted_meds(
            ocr_job_id=ocr_job_id,
            patient_id=ocr_job.patient_id,
            raw_text=raw_text_row.raw_text,
        )
        return await ExtractedMed.filter(ocr_job_id=ocr_job_id).count()

    # REQ-DOC-003, REQ-DOC-004, REQ-DOC-005, REQ-DOC-009 - OCR 비동기 처리 본체
    async def process_ocr_job(self, ocr_job_id: int) -> None:
        ocr_job = await OcrJob.filter(id=ocr_job_id).select_related("document").first()
        if not ocr_job:
            return

        await OcrJob.filter(id=ocr_job.id).update(
            status="processing",
            error_code=None,
            error_message=None,
        )

        try:
            # REQ-DOC-009 - 바코드 인식 우선 시도
            barcode_text = await self._extract_barcode_text(document=ocr_job.document)

            # REQ-DOC-004, REQ-DOC-009 - OCR 텍스트 + 바코드 텍스트 결합
            raw_text = await self._build_combined_raw_text(document=ocr_job.document, barcode_text=barcode_text)
            await self._save_raw_text(ocr_job_id=ocr_job.id, raw_text=raw_text)

            # REQ-DOC-005 - OCR 원문 기반 약 정보 구조화 저장
            await self._save_extracted_meds(ocr_job_id=ocr_job.id, patient_id=ocr_job.patient_id, raw_text=raw_text)

            await OcrJob.filter(id=ocr_job.id).update(status="success")
        except Exception as exc:  # noqa: BLE001
            await OcrJob.filter(id=ocr_job.id).update(
                status="failed",
                error_code=self._build_error_code(exc),
                error_message=str(exc)[:1000],
            )

    # REQ-DOC-004, REQ-DOC-009 - OCR 원문/바코드 결과 결합
    async def _build_combined_raw_text(self, document: Document, barcode_text: str) -> str:
        raw_text_parts: list[str] = []
        if barcode_text:
            raw_text_parts.append(barcode_text.strip())

        ocr_text = ""
        try:
            ocr_text = await self._request_naver_ocr(document=document)
        except RuntimeError as exc:
            # 바코드가 이미 있으면 OCR 공백/설정 누락 케이스는 fallback 허용
            if not raw_text_parts or str(exc) not in {"OCR_EMPTY_RESULT", "NAVER_OCR_CONFIG_MISSING"}:
                raise

        if ocr_text:
            raw_text_parts.append(ocr_text.strip())

        raw_text = "\n".join(part for part in raw_text_parts if part).strip()
        if not raw_text:
            raise RuntimeError("OCR_EMPTY_RESULT")
        return raw_text

    # REQ-DOC-009 - 바코드 인식 결과 추출
    async def _extract_barcode_text(self, document: Document) -> str:
        file_path = self.project_root / document.file_url
        detections = await asyncio.to_thread(self.barcode_service.extract_from_file, file_path)
        if not detections:
            return ""

        lines = ["[BARCODE_DETECTIONS]"]
        for detection in detections:
            lines.append(f"type={detection.barcode_type}, value={detection.barcode_value}")
        return "\n".join(lines)

    # REQ-DOC-003 - 네이버 OCR API 호출
    async def _request_naver_ocr(self, document: Document) -> str:
        if not config.NAVER_OCR_API_URL or not config.NAVER_OCR_SECRET_KEY:
            raise RuntimeError("NAVER_OCR_CONFIG_MISSING")

        file_path = self.project_root / document.file_url
        if not file_path.exists():
            raise RuntimeError("OCR_FILE_NOT_FOUND")

        file_bytes = file_path.read_bytes()
        if not file_bytes:
            raise RuntimeError("OCR_FILE_EMPTY")

        file_format = "pdf" if file_path.suffix.lower() == ".pdf" else "jpg"
        payload = {
            "version": "V2",
            "requestId": uuid.uuid4().hex,
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
            "images": [
                {
                    "format": file_format,
                    "name": file_path.stem or "document",
                    "data": base64.b64encode(file_bytes).decode("utf-8"),
                }
            ],
        }

        headers = {
            "X-OCR-SECRET": config.NAVER_OCR_SECRET_KEY,
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(config.NAVER_OCR_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(config.NAVER_OCR_API_URL, headers=headers, json=payload)

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise RuntimeError(f"NAVER_OCR_HTTP_{response.status_code}")

        data = response.json()
        raw_text = self._extract_raw_text(data=data)
        if not raw_text:
            raise RuntimeError("OCR_EMPTY_RESULT")
        return raw_text

    # REQ-DOC-004 - OCR 원문 텍스트 추출
    @staticmethod
    def _extract_raw_text(data: dict) -> str:
        images = data.get("images") or []
        if not images:
            return ""

        fields = images[0].get("fields") or []
        texts = [str(field.get("inferText", "")).strip() for field in fields if str(field.get("inferText", "")).strip()]
        return "\n".join(texts).strip()

    # REQ-DOC-004 - OCR 원문 저장
    async def _save_raw_text(self, ocr_job_id: int, raw_text: str) -> None:
        existing_raw_text = await OcrRawText.get_or_none(ocr_job_id=ocr_job_id)
        if existing_raw_text:
            await OcrRawText.filter(id=existing_raw_text.id).update(raw_text=raw_text)
            return
        await OcrRawText.create(ocr_job_id=ocr_job_id, raw_text=raw_text)

    # REQ-DOC-005 - OCR 원문 기반 약 정보 구조화 저장
    async def _save_extracted_meds(self, ocr_job_id: int, patient_id: int, raw_text: str) -> None:
        parsed_meds = self._parse_extracted_meds(raw_text=raw_text)

        await ExtractedMed.filter(ocr_job_id=ocr_job_id).delete()
        for parsed_med in parsed_meds:
            await ExtractedMed.create(
                ocr_job_id=ocr_job_id,
                patient_id=patient_id,
                name=parsed_med["name"],
                dosage_text=parsed_med["dosage_text"],
                frequency_text=parsed_med["frequency_text"],
                duration_text=parsed_med["duration_text"],
                confidence=parsed_med["confidence"],
            )

    # REQ-DOC-005 - OCR 원문 파싱(약명/용량/횟수/기간 구조화)
    def _parse_extracted_meds(self, raw_text: str) -> list[dict[str, str | float | None]]:
        lines = [self._normalize_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line and not self._is_noise_line(line)]

        parsed_meds: list[dict[str, str | float | None]] = []
        seen_names: set[str] = set()

        for idx, line in enumerate(lines):
            context_window = lines[idx : idx + 3]
            context_line = " ".join(context_window).strip()

            dosage_text = self._extract_first(line=context_line, pattern=DOSAGE_PATTERN) or self._extract_first(
                line=context_line, pattern=COUNT_DOSAGE_PATTERN
            )
            frequency_text = self._extract_first(line=context_line, pattern=FREQUENCY_PATTERN)
            duration_text = self._extract_first(line=context_line, pattern=DURATION_PATTERN)

            for name in KOREAN_MED_NAME_PATTERN.findall(line):
                normalized_name = self._normalize_med_name(name=name)
                if not self._is_valid_med_name(name=normalized_name):
                    continue

                dedupe_key = normalized_name.casefold()
                if dedupe_key in seen_names:
                    continue
                seen_names.add(dedupe_key)

                parsed_meds.append(
                    {
                        "name": normalized_name,
                        "dosage_text": dosage_text,
                        "frequency_text": frequency_text,
                        "duration_text": duration_text,
                        "confidence": 0.90 if dosage_text else 0.82,
                    }
                )

            # 한국어 제형 패턴으로 못 잡을 때 영문+용량 패턴 fallback
            for match in ENGLISH_MED_WITH_DOSE_PATTERN.findall(line):
                normalized_name = self._normalize_med_name(name=match[0])
                if not self._is_valid_med_name(name=normalized_name):
                    continue

                dedupe_key = normalized_name.casefold()
                if dedupe_key in seen_names:
                    continue
                seen_names.add(dedupe_key)

                parsed_meds.append(
                    {
                        "name": normalized_name,
                        "dosage_text": self._normalize_line(match[1]) or dosage_text,
                        "frequency_text": frequency_text,
                        "duration_text": duration_text,
                        "confidence": 0.80,
                    }
                )

        return parsed_meds

    # REQ-DOC-005 - OCR 파싱 노이즈 라인 제외
    @staticmethod
    def _is_noise_line(line: str) -> bool:
        lowered_line = line.casefold()
        return any(keyword in lowered_line for keyword in NOISE_KEYWORDS)

    # REQ-DOC-005 - OCR 라인 정규화
    @staticmethod
    def _normalize_line(line: str) -> str:
        normalized_line = line.replace("\u200b", " ").strip()
        normalized_line = normalized_line.replace("캅셀", "캡슐").replace("캡셀", "캡슐").replace("캅슐", "캡슐")
        normalized_line = re.sub(r"(서방정|장용캡슐|연질캡슐|캡슐|정)(?=\d)", r"\1 ", normalized_line)
        return re.sub(r"\s+", " ", normalized_line)

    # REQ-DOC-005 - 약명 정규화
    @staticmethod
    def _normalize_med_name(name: str) -> str:
        cleaned_name = re.sub(r"[^A-Za-z가-힣0-9+\-/ ]", "", name)
        cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
        cleaned_name = cleaned_name.replace("캅셀", "캡슐").replace("캡셀", "캡슐").replace("캅슐", "캡슐")
        return cleaned_name

    # REQ-DOC-005 - 일반 제형 단어 오탐 제외
    @staticmethod
    def _is_valid_med_name(name: str) -> bool:
        if not name:
            return False
        normalized = name.strip()
        if not normalized:
            return False
        if normalized in GENERIC_MED_NAMES:
            return False
        if len(normalized) < 3:
            return False
        return True

    # REQ-DOC-005 - 정규식 첫 매치 추출
    @staticmethod
    def _extract_first(line: str, pattern: re.Pattern[str]) -> str | None:
        match = pattern.search(line)
        if not match:
            return None
        return match.group(1).strip()

    # REQ-DOC-001, REQ-DOC-002, REQ-DOC-008 - 문서 접근 권한 확인
    async def _has_patient_access(self, user: User, patient_id: int) -> bool:
        own_patient = await Patient.get_or_none(user_id=user.id)
        if own_patient and own_patient.id == patient_id:
            return True
        return await CaregiverPatientLink.filter(
            caregiver_user_id=user.id,
            patient_id=patient_id,
            status="active",
            revoked_at__isnull=True,
        ).exists()

    # REQ-DOC-008 - OCR 실패 코드 매핑
    @staticmethod
    def _build_error_code(exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "OCR_TIMEOUT"
        if isinstance(exc, httpx.HTTPError):
            return "OCR_HTTP_ERROR"
        return "OCR_FAILED"
