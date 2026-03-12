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

MED_NAME_SUFFIX_PATTERN = "연질캡슐|장용캡슐|경질캡슐|필름코팅정|장용정|서방정|캅셀|캡셀|캅슐|캡슐|정제|정|시럽|현탁액|주사액|주사|크림|로션|패취|패치"
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
PACKED_SCHEDULE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(정|캡슐|알|포|ml|mL)?\s*씩?\s*(\d+)\s*회\s*(\d+)\s*(?:일분|일)",
    re.IGNORECASE,
)
NOISE_KEYWORDS = {
    "[barcode_detections]",
    "type=",
    "환자정보",
    "병원정보",
    "복약안내",
    "조제약사",
    "조제일자",
    "영수증",
    "계산서",
    "약제비",
    "약제비총액",
    "본인부담금",
    "보험자부담금",
    "총수납금액",
    "현금영수증",
    "현금승인번호",
    "신분확인번호",
    "사업장소재지",
    "사업자등록번호",
    "전화",
    "처방전",
    "약품사진",
    "약국",
    "보험",
    "수납",
    "금액",
    "본인전액",
    "공제신청",
    "요구할 수 있습니다",
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
MED_DESCRIPTOR_KEYWORDS = {
    "백색",
    "황색",
    "청색",
    "갈색",
    "담녹색",
    "암녹색",
    "연한",
    "진한",
    "분말",
    "원형",
    "타원형",
    "장방형",
    "정제",
    "경질",
    "연질",
    "필름코팅",
    "완화시켜",
    "배출되도록",
    "약입니다",
}
NON_MED_NAME_KEYWORDS = {
    "약제비",
    "총액",
    "영수증",
    "본인부담금",
    "보험자부담금",
    "본인전액",
    "수납",
    "금액",
    "공제",
    "사업자",
    "신분확인",
    "현금승인",
    "조제약사",
    "병원정보",
    "환자정보",
    "조제일자",
    "복약안내",
    "약품사진",
    "약품명",
    "투약량",
    "횟수",
    "일수",
    "총투",
    "계산",
}
MED_NAME_OCR_CORRECTIONS = {
    "메디락디에스장용캅셀": "메디락디에스장용캡슐",
    "메디락디에스장용캡셀": "메디락디에스장용캡슐",
    "메디락디에스장용캅슐": "메디락디에스장용캡슐",
    "텔미누보정40/5m": "텔미누보정40/5mg",
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

    # 서버 재시작 시 미완료 OCR 작업 자동 재개 - REQ-DOC-003, REQ-DOC-008
    async def resume_pending_ocr_jobs(self, max_jobs: int = 50) -> int:
        if max_jobs <= 0:
            return 0

        pending_jobs = await OcrJob.filter(
            status__in=["queued", "processing"],
            document__status="uploaded",
        ).order_by("-created_at")

        selected_jobs: list[OcrJob] = []
        seen_document_ids: set[int] = set()
        for pending_job in pending_jobs:
            if pending_job.document_id in seen_document_ids:
                continue
            seen_document_ids.add(pending_job.document_id)
            selected_jobs.append(pending_job)
            if len(selected_jobs) >= max_jobs:
                break

        # 오래된 요청부터 순서대로 재개 트리거
        for selected_job in reversed(selected_jobs):
            asyncio.create_task(self.process_ocr_job(ocr_job_id=selected_job.id))
        return len(selected_jobs)

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

        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            file_format = "pdf"
        elif suffix == ".png":
            file_format = "png"
        else:
            file_format = "jpg"
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
        lines = [line for line in lines if line]
        summary_med_names = self._extract_summary_med_names(lines=lines)
        summary_schedule_map = self._extract_summary_schedule_map(lines=lines, summary_med_names=summary_med_names)
        lines = self._extract_medication_section_lines(lines=lines)
        lines = [line for line in lines if not self._is_noise_line(line)]

        parsed_meds: list[dict[str, str | float | None]] = []
        seen_names: set[str] = set()

        for idx, line in enumerate(lines):
            context_window = lines[idx : idx + 8]
            context_line = " ".join(context_window).strip()
            line_for_name = re.split(r"\[", line, maxsplit=1)[0].strip()

            packed_schedule_match = PACKED_SCHEDULE_PATTERN.search(context_line)
            packed_dosage_text = None
            packed_frequency_text = None
            packed_duration_text = None
            if packed_schedule_match:
                packed_dose_count = packed_schedule_match.group(1).strip()
                packed_dose_unit = (packed_schedule_match.group(2) or "").strip().lower()
                packed_frequency_count = packed_schedule_match.group(3).strip()
                packed_duration_days = packed_schedule_match.group(4).strip()
                packed_dosage_text = self._build_dosage_text_from_count(
                    med_name=line_for_name,
                    dose_count=packed_dose_count,
                    explicit_unit=packed_dose_unit,
                )
                packed_frequency_text = f"{packed_frequency_count}회"
                packed_duration_text = f"{packed_duration_days}일분"

            dosage_text = self._extract_first(line=context_line, pattern=DOSAGE_PATTERN) or self._extract_first(
                line=context_line, pattern=COUNT_DOSAGE_PATTERN
            )
            frequency_text = self._extract_first(line=context_line, pattern=FREQUENCY_PATTERN)
            duration_text = self._extract_first(line=context_line, pattern=DURATION_PATTERN)

            for name in KOREAN_MED_NAME_PATTERN.findall(line_for_name):
                normalized_name = self._normalize_med_name(name=name)
                if not self._is_valid_med_name(name=normalized_name):
                    continue

                dedupe_key = normalized_name.casefold()
                if dedupe_key in seen_names:
                    continue
                seen_names.add(dedupe_key)

                schedule_from_summary = self._find_schedule_from_summary(
                    med_name=normalized_name,
                    summary_schedule_map=summary_schedule_map,
                )

                parsed_meds.append(
                    {
                        "name": normalized_name,
                        "dosage_text": self._resolve_dosage_text_for_output(
                            dosage_text=dosage_text,
                            packed_dosage_text=packed_dosage_text,
                            schedule_from_summary=schedule_from_summary,
                        ),
                        "frequency_text": (
                            frequency_text
                            or packed_frequency_text
                            or (schedule_from_summary["frequency_text"] if schedule_from_summary else None)
                        ),
                        "duration_text": (
                            duration_text
                            or packed_duration_text
                            or (schedule_from_summary["duration_text"] if schedule_from_summary else None)
                        ),
                        "confidence": 0.90 if dosage_text else 0.82,
                    }
                )

            # 한국어 제형 패턴으로 못 잡을 때 영문+용량 패턴 fallback
            for match in ENGLISH_MED_WITH_DOSE_PATTERN.findall(line_for_name):
                normalized_name = self._normalize_med_name(name=match[0])
                if not self._is_valid_med_name(name=normalized_name):
                    continue

                dedupe_key = normalized_name.casefold()
                if dedupe_key in seen_names:
                    continue
                seen_names.add(dedupe_key)

                schedule_from_summary = self._find_schedule_from_summary(
                    med_name=normalized_name,
                    summary_schedule_map=summary_schedule_map,
                )

                parsed_meds.append(
                    {
                        "name": normalized_name,
                        "dosage_text": self._resolve_dosage_text_for_output(
                            dosage_text=(self._normalize_line(match[1]) or dosage_text),
                            packed_dosage_text=packed_dosage_text,
                            schedule_from_summary=schedule_from_summary,
                        ),
                        "frequency_text": frequency_text
                        or packed_frequency_text
                        or (schedule_from_summary["frequency_text"] if schedule_from_summary else None),
                        "duration_text": duration_text
                        or packed_duration_text
                        or (schedule_from_summary["duration_text"] if schedule_from_summary else None),
                        "confidence": 0.80,
                    }
                )

        # OCR 오탐(영수증/설명 문구 등) 최소화 - REQ-DOC-005
        parsed_meds = [med for med in parsed_meds if self._is_useful_parsed_med(parsed_med=med)]

        if summary_med_names:
            parsed_meds = self._filter_parsed_meds_with_summary(
                parsed_meds=parsed_meds,
                summary_med_names=summary_med_names,
                summary_schedule_map=summary_schedule_map,
            )

        return parsed_meds

    # REQ-DOC-005 - OCR 용량값과 summary 용량값 우선순위 정리
    @staticmethod
    def _resolve_dosage_text_for_output(
        dosage_text: str | None,
        packed_dosage_text: str | None,
        schedule_from_summary: dict[str, str | None] | None,
    ) -> str | None:
        summary_dosage_text = schedule_from_summary["dosage_text"] if schedule_from_summary else None
        candidate_dosage_text = dosage_text or packed_dosage_text or summary_dosage_text
        if not candidate_dosage_text:
            return None

        if summary_dosage_text and dosage_text:
            compact_dosage_text = dosage_text.replace(" ", "").lower()
            has_count_unit = bool(re.search(r"(정|캡슐|알|포|t)$", compact_dosage_text))
            is_strength_only = bool(re.search(r"(mg|g|mcg|ml)$", compact_dosage_text))
            if is_strength_only and not has_count_unit:
                return summary_dosage_text
        return candidate_dosage_text

    # REQ-DOC-005 - 하단 약품명/투약량/횟수/일수 표에서 복약 스케줄 추출
    def _extract_summary_schedule_map(
        self, lines: list[str], summary_med_names: list[str]
    ) -> dict[str, dict[str, str | None]]:
        if not summary_med_names:
            return {}
        summary_header_idx = self._find_summary_header_index(lines=lines)
        if summary_header_idx is None:
            return {}

        schedule_map: dict[str, dict[str, str | None]] = {}
        summary_lines = lines[summary_header_idx + 1 :]

        idx = 0
        while idx < len(summary_lines):
            current_line = summary_lines[idx].strip()
            if "본인의 약은" in current_line or "처방조제된 약은" in current_line:
                break

            is_med_line = self._is_possible_summary_med_line(
                current_line
            ) or self._is_possible_summary_name_from_numeric_row(
                line=current_line, next_lines=summary_lines[idx + 1 : idx + 5]
            )
            if not is_med_line:
                idx += 1
                continue

            med_name = self._normalize_med_name(name=current_line.lstrip("+").strip())
            med_name = re.sub(r"(?<=\d)m$", "mg", med_name, flags=re.IGNORECASE)
            med_key = self._normalize_name_for_compare(name=med_name)
            if not med_key:
                idx += 1
                continue

            numeric_values, cursor = self._extract_numeric_values_after_line(
                summary_lines=summary_lines, start_idx=idx + 1
            )

            if len(numeric_values) >= 3:
                dose_count = numeric_values[0]
                frequency_count = numeric_values[1]
                duration_days = numeric_values[2]
                schedule_map[med_key] = {
                    "dosage_text": self._build_dosage_text_from_count(med_name=med_name, dose_count=dose_count),
                    "frequency_text": f"{frequency_count}회",
                    "duration_text": f"{duration_days}일분",
                }
                idx = cursor
                continue

            idx += 1

        return schedule_map

    # REQ-DOC-005 - summary 표 헤더 인덱스 탐색
    @staticmethod
    def _find_summary_header_index(lines: list[str]) -> int | None:
        for idx in range(len(lines)):
            window = " ".join(lines[idx : idx + 8])
            if "약품명" in window and "투약량" in window and "횟수" in window and "일수" in window and "총투" in window:
                return idx
        return None

    # REQ-DOC-005 - summary 표 숫자열 추출
    @staticmethod
    def _extract_numeric_values_after_line(summary_lines: list[str], start_idx: int) -> tuple[list[str], int]:
        numeric_values: list[str] = []
        cursor = start_idx
        while cursor < len(summary_lines) and len(numeric_values) < 4:
            value_line = summary_lines[cursor].strip()
            if re.fullmatch(r"\d+", value_line):
                numeric_values.append(value_line)
                cursor += 1
                continue
            break
        return numeric_values, cursor

    # REQ-DOC-005 - OCR 텍스트에서 복약 표 영역만 우선 추출
    @staticmethod
    def _extract_medication_section_lines(lines: list[str]) -> list[str]:
        if not lines:
            return lines

        section_start_idx: int | None = None
        for idx in range(len(lines)):
            window = " ".join(lines[idx : idx + 8])
            if "약품사진" in window and "약품명" in window and "복약안내" in window:
                section_start_idx = idx
                break
        if section_start_idx is None:
            for idx in range(len(lines)):
                window = " ".join(lines[idx : idx + 8])
                if "약품명" in window and "복약안내" in window:
                    section_start_idx = idx
                    break

        if section_start_idx is None:
            return lines

        section_end_idx = len(lines)
        for idx in range(section_start_idx + 12, len(lines)):
            window = " ".join(lines[idx : idx + 8])
            if "약품명" in window and "투약량" in window and "횟수" in window and "일수" in window:
                section_end_idx = idx
                break

        return lines[section_start_idx:section_end_idx]

    # REQ-DOC-005 - 하단 약품명/투약량 표에서 약명 후보 추출
    def _extract_summary_med_names(self, lines: list[str]) -> list[str]:
        summary_header_idx: int | None = None
        for idx in range(len(lines)):
            window = " ".join(lines[idx : idx + 8])
            if "약품명" in window and "투약량" in window and "횟수" in window and "일수" in window and "총투" in window:
                summary_header_idx = idx
                break

        if summary_header_idx is None:
            return []

        summary_names: list[str] = []
        seen_keys: set[str] = set()
        summary_lines = lines[summary_header_idx + 1 :]
        for idx, line in enumerate(summary_lines):
            if "본인의 약은" in line or "처방조제된 약은" in line:
                break
            is_summary_med_line = self._is_possible_summary_med_line(line=line)
            if not is_summary_med_line:
                is_summary_med_line = self._is_possible_summary_name_from_numeric_row(
                    line=line, next_lines=summary_lines[idx + 1 : idx + 5]
                )
            if not is_summary_med_line:
                continue

            normalized_name = self._normalize_med_name(name=line.lstrip("+").strip())
            normalized_name = re.sub(r"(?<=\d)m$", "mg", normalized_name, flags=re.IGNORECASE)
            if not self._is_valid_med_name(name=normalized_name):
                continue

            compare_key = self._normalize_name_for_compare(name=normalized_name)
            if not compare_key or compare_key in seen_keys:
                continue
            seen_keys.add(compare_key)
            summary_names.append(normalized_name)

        return summary_names

    # REQ-DOC-005 - summary 표 약명 후보 라인 판별
    @staticmethod
    def _is_possible_summary_med_line(line: str) -> bool:  # noqa: C901
        candidate = line.strip()
        if not candidate:
            return False
        if candidate in {"약품명", "투약량", "횟수", "일수", "총투"}:
            return False
        if re.fullmatch(r"[0-9\s,./()\-+:℃%]+", candidate):
            return False
        if len(candidate) > 30 or len(candidate) < 4:
            return False
        if not re.search(r"[A-Za-z가-힣]", candidate):
            return False
        tokens = candidate.split()
        if len(tokens) >= 3:
            return False
        if len(tokens) == 2 and not re.fullmatch(r"\d+(?:\.\d+)?/\d+(?:\.\d+)?m?g?", tokens[1], re.IGNORECASE):
            return False
        if "1정씩" in candidate or "1캡슐" in candidate or "1포씩" in candidate:
            return False
        if any(keyword in candidate for keyword in MED_DESCRIPTOR_KEYWORDS):
            return False
        if any(
            keyword in candidate
            for keyword in {"주의", "보관", "복용", "용량", "치료제", "입니다", "요법", "안지오텐신", "수용체"}
        ):
            return False
        has_med_suffix = bool(re.search(r"(캡슐|정|정제|시럽|현탁액|주사|크림|로션|패치|패취)$", candidate))
        has_dose_pattern = bool(re.search(r"\d+(?:\.\d+)?/\d+(?:\.\d+)?m?g?$", candidate, flags=re.IGNORECASE))
        has_extended_name = bool(re.search(r"\d+시간이알$", candidate))
        if not (has_med_suffix or has_dose_pattern or has_extended_name):
            return False
        return True

    # REQ-DOC-005 - suffix 누락 약명의 숫자열 행 패턴 보정
    @staticmethod
    def _is_possible_summary_name_from_numeric_row(line: str, next_lines: list[str]) -> bool:
        candidate = line.strip().replace("+", "")
        if not candidate or " " in candidate:
            return False
        if len(candidate) < 6:
            return False
        if not re.search(r"[A-Za-z가-힣]", candidate):
            return False
        if any(keyword in candidate for keyword in MED_DESCRIPTOR_KEYWORDS):
            return False
        if any(keyword in candidate for keyword in {"주의", "보관", "복용", "용량", "치료제", "입니다"}):
            return False

        numeric_count = 0
        for next_line in next_lines:
            if re.fullmatch(r"\d+", next_line.strip()):
                numeric_count += 1
            else:
                break
        return numeric_count >= 3

    # REQ-DOC-005 - summary 기반 오탐 필터링 + 누락 약명 보정
    def _filter_parsed_meds_with_summary(
        self,
        parsed_meds: list[dict[str, str | float | None]],
        summary_med_names: list[str],
        summary_schedule_map: dict[str, dict[str, str | None]],
    ) -> list[dict[str, str | float | None]]:
        summary_keys = [self._normalize_name_for_compare(name=name) for name in summary_med_names]
        summary_keys = [key for key in summary_keys if key]

        filtered_meds: list[dict[str, str | float | None]] = []
        matched_summary_keys: set[str] = set()

        for parsed_med in parsed_meds:
            med_name = str(parsed_med.get("name") or "")
            med_key = self._normalize_name_for_compare(name=med_name)
            if not med_key:
                continue

            matched_key = next((key for key in summary_keys if self._is_same_med_key(med_key, key)), None)
            if not matched_key:
                continue

            filtered_meds.append(parsed_med)
            matched_summary_keys.add(matched_key)

        existing_keys = {self._normalize_name_for_compare(name=str(med.get("name") or "")) for med in filtered_meds}
        for summary_name in summary_med_names:
            summary_key = self._normalize_name_for_compare(name=summary_name)
            if not summary_key:
                continue
            if any(self._is_same_med_key(summary_key, existing_key) for existing_key in existing_keys if existing_key):
                continue
            schedule = summary_schedule_map.get(summary_key)
            filtered_meds.append(
                {
                    "name": summary_name,
                    "dosage_text": schedule["dosage_text"] if schedule else None,
                    "frequency_text": schedule["frequency_text"] if schedule else None,
                    "duration_text": schedule["duration_text"] if schedule else None,
                    "confidence": 0.70,
                }
            )
            existing_keys.add(summary_key)

        return filtered_meds or parsed_meds

    # REQ-DOC-005 - 약명 비교용 키 정규화
    def _normalize_name_for_compare(self, name: str) -> str:
        normalized_name = self._normalize_med_name(name=name)
        normalized_name = re.sub(r"(?<=\d)m$", "mg", normalized_name, flags=re.IGNORECASE)
        normalized_name = re.sub(r"\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL)$", "", normalized_name, flags=re.IGNORECASE)
        normalized_name = re.sub(
            r"\d+(?:\.\d+)?/\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL)?$",
            "",
            normalized_name,
            flags=re.IGNORECASE,
        )
        normalized_name = re.sub(r"[^A-Za-z가-힣0-9]", "", normalized_name)
        return normalized_name.casefold().strip()

    # REQ-DOC-005 - summary 기반 스케줄 매핑 조회
    def _find_schedule_from_summary(
        self, med_name: str, summary_schedule_map: dict[str, dict[str, str | None]]
    ) -> dict[str, str | None] | None:
        med_key = self._normalize_name_for_compare(name=med_name)
        if not med_key:
            return None
        direct_schedule = summary_schedule_map.get(med_key)
        if direct_schedule:
            return direct_schedule
        for summary_key, schedule in summary_schedule_map.items():
            if self._is_same_med_key(med_key, summary_key):
                return schedule
        return None

    # REQ-DOC-005 - 투약량 숫자를 약 형태에 맞춰 문자열로 변환
    @staticmethod
    def _build_dosage_text_from_count(med_name: str, dose_count: str, explicit_unit: str = "") -> str:
        normalized_unit = explicit_unit.lower()
        if normalized_unit in {"정", "capsule", "캡슐", "알", "포", "ml"}:
            unit_text = "캡슐" if normalized_unit == "capsule" else normalized_unit
            return f"{dose_count}{unit_text}씩"

        normalized_name = med_name.replace(" ", "")
        if "시럽" in normalized_name:
            return f"{dose_count}포씩"
        if "캡슐" in normalized_name:
            return f"{dose_count}캡슐씩"
        return f"{dose_count}정씩"

    # REQ-DOC-005 - 약명 키 유사도 비교
    @staticmethod
    def _is_same_med_key(left_key: str, right_key: str) -> bool:
        if not left_key or not right_key:
            return False
        if left_key == right_key:
            return True
        min_len = min(len(left_key), len(right_key))
        if min_len < 4:
            return False
        return left_key in right_key or right_key in left_key

    # REQ-DOC-005 - OCR 파싱 노이즈 라인 제외
    @staticmethod
    def _is_noise_line(line: str) -> bool:
        lowered_line = line.casefold()
        if any(keyword in lowered_line for keyword in NOISE_KEYWORDS):
            return True
        if re.fullmatch(r"[0-9\s,./()\-+:℃%]+", line):
            return True
        return len(re.sub(r"\s+", "", line)) <= 1

    # REQ-DOC-005 - OCR 라인 정규화
    @staticmethod
    def _normalize_line(line: str) -> str:
        normalized_line = line.replace("\u200b", " ").strip()
        normalized_line = normalized_line.replace("캅셀", "캡슐").replace("캡셀", "캡슐").replace("캅슐", "캡슐")
        normalized_line = re.sub(r"(?<=\d)m(?=\s|$)", "mg", normalized_line, flags=re.IGNORECASE)
        normalized_line = re.sub(r"(서방정|장용캡슐|연질캡슐|캡슐|정)(?=\d)", r"\1 ", normalized_line)
        return re.sub(r"\s+", " ", normalized_line)

    # REQ-DOC-005 - 약명 정규화
    @staticmethod
    def _normalize_med_name(name: str) -> str:
        cleaned_name = re.sub(r"[^A-Za-z가-힣0-9+\-/ ]", "", name)
        cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
        cleaned_name = cleaned_name.replace("캅셀", "캡슐").replace("캡셀", "캡슐").replace("캅슐", "캡슐")
        cleaned_name = re.sub(r"(?<=\d)m$", "mg", cleaned_name, flags=re.IGNORECASE)
        corrected_name = MED_NAME_OCR_CORRECTIONS.get(cleaned_name)
        if corrected_name:
            return corrected_name
        return cleaned_name

    # REQ-DOC-005 - 일반 제형 단어 오탐 제외
    @staticmethod
    def _is_valid_med_name(name: str) -> bool:
        if not name:
            return False
        normalized = name.strip()
        if not normalized:
            return False
        compact_name = re.sub(r"\s+", "", normalized).replace("+", "")
        if OcrService._contains_non_med_keyword(compact_name=compact_name):
            return False
        if compact_name in GENERIC_MED_NAMES:
            return False
        if len(compact_name) <= 3 and compact_name.endswith("정"):
            return False
        if OcrService._looks_like_descriptor_noise(compact_name=compact_name):
            return False
        if len(compact_name) < 3:
            return False
        if compact_name.endswith(("해주", "시켜주", "와주는", "배출되도록")):
            return False
        return True

    # REQ-DOC-005 - 비약품 키워드 포함 여부 검사
    @staticmethod
    def _contains_non_med_keyword(compact_name: str) -> bool:
        return any(keyword in compact_name for keyword in NON_MED_NAME_KEYWORDS)

    # REQ-DOC-005 - 설명문/제형 묘사 문구 오탐 검사
    @staticmethod
    def _looks_like_descriptor_noise(compact_name: str) -> bool:
        if not any(keyword in compact_name for keyword in MED_DESCRIPTOR_KEYWORDS):
            return False
        if compact_name.endswith(("정", "정제", "캡슐", "시럽")) and len(compact_name) <= 10:
            return True
        return any(keyword in compact_name for keyword in {"완화시켜", "배출되도록", "약입니다", "분말", "원형"})

    # REQ-DOC-005 - 최종 추출약 유효성(스케줄 정보/약명 길이) 판별
    @staticmethod
    def _is_useful_parsed_med(parsed_med: dict[str, str | float | None]) -> bool:
        med_name = str(parsed_med.get("name") or "").strip()
        if not med_name:
            return False

        has_schedule = any(
            parsed_med.get(field_name) for field_name in ("dosage_text", "frequency_text", "duration_text")
        )
        if has_schedule:
            return True

        compact_name = re.sub(r"\s+", "", med_name)
        if len(compact_name) >= 5:
            return True
        if compact_name.endswith(("캡슐", "시럽", "현탁액", "주사", "패치", "패취")):
            return True
        return False

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
