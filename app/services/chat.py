from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.dtos.chat import (
    ChatMessageCreateData,
    ChatMessageCreateResponse,
    ChatMessageItem,
    ChatMessageListData,
    ChatMessageListResponse,
    ChatSessionCreateData,
    ChatSessionCreateResponse,
    RequesterRole,
)
from app.models.chat import ChatMessage, ChatSession
from app.models.guides import Guide, GuideStatus
from app.models.medications import PatientMed
from app.models.patients import CaregiverPatientLink, Patient, PatientProfile
from app.models.schedules import MedSchedule, MedScheduleTime
from app.models.users import User
from app.services.kids_client import KIDSClient
from app.services.rag import (
    build_rag_context,
    extract_external_blocks,
    extract_guide_blocks,
    extract_meds_blocks,
    extract_profile_blocks,
    extract_schedule_blocks,
)

logger = logging.getLogger(__name__)

CHAT_DISCLAIMER = "본 답변은 의료 자문이 아닌 참고용 정보입니다."
CHAT_HISTORY_TURNS = int((os.getenv("CHAT_HISTORY_TURNS", "8") or "8").strip())
CHAT_MAX_MESSAGE_CHARS = int((os.getenv("CHAT_MAX_MESSAGE_CHARS", "2000") or "2000").strip())
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_EMERGENCY_KEYWORDS = [
    "숨이 차",
    "호흡곤란",
    "숨쉬기 힘들",
    "가슴 통증",
    "의식이 흐려",
    "실신",
    "경련",
    "피가 나",
    "출혈",
    "극심한 통증",
    "응급실",
    "119",
]

_PROFILE_SMOKING_KEYWORDS = ["담배", "흡연", "몇 갑", "주에 평균", "주간 흡연"]
_PROFILE_ALCOHOL_KEYWORDS = ["술", "음주", "몇 병", "주간 음주"]
_PROFILE_SLEEP_KEYWORDS = ["수면", "잠", "몇 시간"]
_PROFILE_EXERCISE_KEYWORDS = ["운동", "몇 분", "운동량"]
_SCHEDULE_KEYWORDS = ["복약스케줄", "복약 스케줄", "언제 먹", "언제 복용", "몇 시", "스케줄", "일정"]
_GUIDE_SUMMARY_KEYWORDS = ["전반적", "가이드", "약 설명", "무슨 약"]
_MEDICATION_CAUTION_KEYWORDS = [
    "주의사항",
    "주의할 점",
    "주의해야 할 점",
    "주의해야할 점",
    "조심",
    "부작용",
    "상호작용",
    "금기",
    "주의점",
    "조심할 점",
]
_DAILY_CHAT_KEYWORDS = [
    "안녕",
    "반가워",
    "고마워",
    "감사",
    "이름이 뭐",
    "너 이름",
    "누구야",
    "오늘 어때",
    "오늘 하루",
    "기분 어때",
    "잘 자",
    "좋은 아침",
]


class ChatServiceError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass
class PatientChatContext:
    patient_id: int
    profile: PatientProfile | None
    latest_guide: Guide | None
    meds: list[dict[str, Any]]
    schedules: list[dict[str, Any]]
    recent_messages: list[ChatMessage]
    kids_evidence: list[dict[str, Any]]
    rag_context: list[dict[str, Any]]


# 요청자 역할 판별
async def _resolve_requester_role(user_id: int) -> RequesterRole:
    patient_exists = await Patient.filter(user_id=user_id).exists()
    if patient_exists:
        return RequesterRole.PATIENT

    caregiver_exists = await CaregiverPatientLink.filter(
        caregiver_user_id=user_id,
        status="active",
    ).exists()
    if caregiver_exists:
        return RequesterRole.CAREGIVER

    return RequesterRole.ADMIN


# 프롬프트 파일 읽기
def _read_prompt_template(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise RuntimeError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


# 응급 키워드 감지
def _detect_emergency(message: str) -> tuple[bool, str | None]:
    normalized = (message or "").strip()
    for keyword in _EMERGENCY_KEYWORDS:
        if keyword in normalized:
            return (
                True,
                "응급 상황이 의심됩니다. 즉시 119 또는 가까운 응급실/의료기관에 연락해 주세요.",
            )
    return False, None


# 현재 연도
def date_today_year() -> int:
    from datetime import date

    return date.today().year


# 연령대 분류
def _resolve_audience(profile: PatientProfile | None) -> str:
    birth_year = getattr(profile, "birth_year", None)
    if not birth_year:
        return "adult"

    age = date_today_year() - int(birth_year)

    if age <= 12:
        return "child"
    if 13 <= age <= 18:
        return "teen"
    if age >= 65:
        return "senior"
    return "adult"


# 설명 라벨
def _audience_label(audience: str) -> str:
    if audience == "child":
        return "아이용 아주 쉬운 설명"
    if audience == "teen":
        return "청소년용 쉬운 설명"
    if audience == "senior":
        return "고령자용 주의 강화 설명"
    return "성인용 일반 설명"


# 추가 안전 문구
def _extra_safety_text(audience: str) -> str:
    if audience == "child":
        return "아이의 경우 보호자 확인이 중요하며 어려운 의학용어를 피한다."
    if audience == "teen":
        return "청소년은 이해하기 쉬운 설명으로 답하고 복약 실수를 줄이도록 돕는다."
    if audience == "senior":
        return "65세 이상은 어지러움, 낙상, 복약 시간 혼동, 보호자 확인 필요성을 함께 고려한다."
    return "제공된 근거 범위 안에서 일반 성인 기준으로 설명한다."


# 건강 프로필 텍스트 구성
def _build_profile_text(profile: PatientProfile | None) -> str:
    if not profile:
        return "등록된 건강 프로필 없음"

    lines: list[str] = []
    if getattr(profile, "birth_year", None):
        lines.append(f"- 출생연도: {profile.birth_year}")
    if getattr(profile, "sex", None):
        lines.append(f"- 성별: {profile.sex}")
    if getattr(profile, "height_cm", None) is not None:
        lines.append(f"- 키(cm): {profile.height_cm}")
    if getattr(profile, "weight_kg", None) is not None:
        lines.append(f"- 체중(kg): {profile.weight_kg}")
    if getattr(profile, "bmi", None) is not None:
        lines.append(f"- BMI: {profile.bmi}")
    if getattr(profile, "conditions", None):
        lines.append(f"- 기저질환/상태: {profile.conditions}")
    if getattr(profile, "allergies", None):
        lines.append(f"- 알레르기: {profile.allergies}")
    if getattr(profile, "notes", None):
        lines.append(f"- 메모: {profile.notes}")
    if getattr(profile, "is_smoker", None) is not None:
        lines.append(f"- 흡연 여부: {'예' if profile.is_smoker else '아니오'}")
    if getattr(profile, "avg_cig_packs_per_week", None) is not None:
        lines.append(f"- 주간 흡연량: {profile.avg_cig_packs_per_week}갑")
    if getattr(profile, "avg_alcohol_bottles_per_week", None) is not None:
        lines.append(f"- 주간 음주량: {profile.avg_alcohol_bottles_per_week}병")
    if getattr(profile, "avg_sleep_hours_per_day", None) is not None:
        lines.append(f"- 평균 수면 시간: {profile.avg_sleep_hours_per_day}시간")
    if getattr(profile, "avg_exercise_minutes_per_day", None) is not None:
        lines.append(f"- 평균 운동 시간: {profile.avg_exercise_minutes_per_day}분")
    if getattr(profile, "is_hospitalized", None) is not None:
        lines.append(f"- 입원 여부: {'예' if profile.is_hospitalized else '아니오'}")

    return "\n".join(lines) if lines else "등록된 건강 프로필 없음"


# 약 정보 텍스트 구성
def _build_meds_text(meds: list[dict[str, Any]]) -> str:
    if not meds:
        return "현재 복용 약 정보 없음"

    lines: list[str] = []
    for med in meds:
        display_name = med.get("display_name") or "약 이름 없음"
        dosage = med.get("dosage")
        route = med.get("route")

        chunks = [display_name]
        if dosage:
            chunks.append(f"용량={dosage}")
        if route:
            chunks.append(f"경로={route}")

        lines.append("- " + " / ".join(chunks))

    return "\n".join(lines)


# 시간 문구 변환
def _humanize_time(time_text: str | None) -> str:
    if not time_text:
        return "시간 미설정"

    raw = str(time_text).strip()
    hour = None
    minute = 0

    try:
        parts = raw.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return raw

    if hour == 0 and minute == 0:
        return "자정"
    if hour < 12:
        prefix = "오전"
        shown_hour = 12 if hour == 0 else hour
    elif hour == 12:
        prefix = "정오"
        shown_hour = 12
    else:
        prefix = "오후"
        shown_hour = hour - 12

    if prefix == "정오":
        return "정오" if minute == 0 else f"정오 {minute}분"

    if minute == 0:
        return f"{prefix} {shown_hour}시"
    return f"{prefix} {shown_hour}시 {minute}분"


# 요일 문구 변환
def _humanize_days(days_text: str | None) -> str:
    if not days_text:
        return "요일 정보 없음"

    normalized = str(days_text).replace(" ", "")
    if normalized in {"1,2,3,4,5,6,7", "1,2,3,4,5,6,7,"}:
        return "매일"

    day_map = {
        "1": "월",
        "2": "화",
        "3": "수",
        "4": "목",
        "5": "금",
        "6": "토",
        "7": "일",
    }
    items = [day_map.get(x, x) for x in normalized.split(",") if x]
    return ",".join(items) if items else "요일 정보 없음"


# 일정 텍스트 구성
def _build_schedule_text(schedules: list[dict[str, Any]], meds: list[dict[str, Any]]) -> str:
    if not schedules:
        return "등록된 복약 일정 없음"

    med_name_map: dict[int, str] = {}
    for med in meds:
        patient_med_id = med.get("patient_med_id")
        display_name = med.get("display_name")
        if patient_med_id is not None and display_name:
            med_name_map[int(patient_med_id)] = str(display_name)

    lines: list[str] = []
    for schedule in schedules:
        patient_med_id = int(schedule.get("patient_med_id"))
        med_name = med_name_map.get(patient_med_id, f"patient_med_id={patient_med_id}")
        times = schedule.get("times") or []

        if not times:
            lines.append(f"- {med_name}: 시간 정보 없음")
            continue

        for item in times:
            time_label = _humanize_time(item.get("time_of_day"))
            days_label = _humanize_days(item.get("days_of_week"))

            if days_label == "요일 정보 없음" and time_label == "시간 미설정":
                lines.append(f"- {med_name}: 복용 시간 정보가 등록되어 있지 않습니다.")
            elif days_label == "요일 정보 없음":
                lines.append(f"- {med_name}: {time_label}에 복용하도록 기록되어 있습니다.")
            elif time_label == "시간 미설정":
                lines.append(f"- {med_name}: {days_label} 복용으로 기록되어 있으나 시간 정보는 없습니다.")
            elif days_label == "매일":
                lines.append(f"- {med_name}: 매일 {time_label}")
            else:
                lines.append(f"- {med_name}: {days_label} {time_label}")

    return "\n".join(lines) if lines else "등록된 복약 일정 없음"


# 최신 guide 텍스트 구성
def _build_guide_text(guide: Guide | None) -> str:
    if not guide:
        return "최신 guide 없음"

    sections: list[str] = []
    if guide.content_text:
        sections.append(f"[guide 본문]\n{guide.content_text}")
    if isinstance(guide.content_json, dict):
        sections.append(f"[guide 구조화]\n{json.dumps(guide.content_json, ensure_ascii=False)}")
    if isinstance(guide.caregiver_summary, dict):
        sections.append(f"[caregiver summary]\n{json.dumps(guide.caregiver_summary, ensure_ascii=False)}")

    return "\n\n".join(sections) if sections else "최신 guide 없음"


# 최근 대화 텍스트 구성
def _build_history_text(messages: list[ChatMessage]) -> str:
    if not messages:
        return "이전 대화 없음"

    lines: list[str] = []
    for msg in messages:
        lines.append(f"- {msg.role}: {msg.content}")
    return "\n".join(lines)


# KIDS evidence 텍스트 구성
def _build_kids_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return "KIDS 안전성 근거 없음"
    return json.dumps(items, ensure_ascii=False)


# RAG context 텍스트 구성
def _build_rag_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return "RAG 참고 근거 없음"
    return json.dumps(items, ensure_ascii=False)


# 최신 guide 조회
async def _get_latest_done_guide(patient_id: int) -> Guide | None:
    return await Guide.filter(patient_id=patient_id, status=GuideStatus.DONE).order_by("-created_at", "-id").first()


# 현재 복용 약 조회
async def _get_active_meds(patient_id: int) -> list[dict[str, Any]]:
    rows = (
        await PatientMed.filter(
            patient_id=patient_id,
            is_active=True,
            confirmed_at__not_isnull=True,
        )
        .order_by("id")
        .all()
    )

    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "patient_med_id": int(row.id),
                "display_name": row.display_name,
                "dosage": row.dosage,
                "route": row.route,
            }
        )
    return results


# 현재 복약 일정 조회
async def _get_active_schedules(patient_id: int) -> list[dict[str, Any]]:
    schedules = await MedSchedule.filter(
        patient_id=patient_id,
        status="active",
    ).all()

    if not schedules:
        return []

    schedule_ids = [int(s.id) for s in schedules]
    schedule_times = await MedScheduleTime.filter(
        schedule_id__in=schedule_ids,
        is_active=True,
    ).all()

    time_map: dict[int, list[dict[str, Any]]] = {}
    for item in schedule_times:
        schedule_id = int(item.schedule_id)
        time_map.setdefault(schedule_id, []).append(
            {
                "time_of_day": str(item.time_of_day) if item.time_of_day else None,
                "days_of_week": item.days_of_week,
            }
        )

    results: list[dict[str, Any]] = []
    for schedule in schedules:
        results.append(
            {
                "schedule_id": int(schedule.id),
                "patient_med_id": int(schedule.patient_med_id),
                "times": time_map.get(int(schedule.id), []),
            }
        )

    return results


# 건강 프로필 조회
async def _get_profile(patient_id: int) -> PatientProfile | None:
    return await PatientProfile.get_or_none(patient_id=patient_id, is_deleted=False)


# KIDS
async def _build_kids_evidence(*, meds: list[dict[str, Any]], profile: PatientProfile | None) -> list[dict[str, Any]]:
    del profile

    client = KIDSClient()
    if not client.is_enabled():
        return []

    evidence: list[dict[str, Any]] = []
    for med in meds[:5]:
        drug_name = str(med.get("display_name") or "").strip()
        if not drug_name:
            continue
        items = await client.search_safety_evidence(drug_name)
        evidence.extend(items)

    return evidence[:10]


# RAG용 텍스트 블록 추가 헬퍼
def _append_rag_block(blocks: list[dict[str, Any]], *, source: str, title: str, content: str) -> None:
    text = (content or "").strip()
    if not text:
        return
    blocks.append(
        {
            "source": source,
            "title": title,
            "content": text,
        }
    )


# 최신 guide에서 RAG 블록 추출
def _extract_guide_rag_blocks(guide: Guide | None) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if not guide:
        return blocks

    if guide.content_text:
        _append_rag_block(
            blocks,
            source="guide_text",
            title="최신 가이드 본문",
            content=guide.content_text,
        )

    if isinstance(guide.content_json, dict):
        sections = guide.content_json.get("sections") or []
        for section in sections:
            title = str(section.get("title") or "가이드 섹션")
            body = str(section.get("body") or "")
            _append_rag_block(
                blocks,
                source="guide_section",
                title=title,
                content=body,
            )

    if isinstance(guide.caregiver_summary, dict):
        _append_rag_block(
            blocks,
            source="guide_caregiver_summary",
            title="보호자 요약",
            content=json.dumps(guide.caregiver_summary, ensure_ascii=False),
        )

    return blocks


# 프로필에서 RAG 블록 추출
def _extract_profile_rag_blocks(profile: PatientProfile | None) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if not profile:
        return blocks

    profile_map = {
        "흡연 정보": getattr(profile, "avg_cig_packs_per_week", None),
        "음주 정보": getattr(profile, "avg_alcohol_bottles_per_week", None),
        "수면 정보": getattr(profile, "avg_sleep_hours_per_day", None),
        "운동 정보": getattr(profile, "avg_exercise_minutes_per_day", None),
        "기저질환": getattr(profile, "conditions", None),
        "알레르기": getattr(profile, "allergies", None),
        "메모": getattr(profile, "notes", None),
    }

    for title, value in profile_map.items():
        if value is not None and str(value).strip():
            _append_rag_block(
                blocks,
                source="profile",
                title=title,
                content=str(value),
            )

    return blocks


# 스케줄에서 RAG 블록 추출
def _extract_schedule_rag_blocks(meds: list[dict[str, Any]], schedules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    schedule_text = _build_schedule_text(schedules, meds)
    if schedule_text != "등록된 복약 일정 없음":
        _append_rag_block(
            blocks,
            source="schedule",
            title="복약 일정",
            content=schedule_text,
        )
    return blocks


# 약 정보에서 RAG 블록 추출
def _extract_meds_rag_blocks(meds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    meds_text = _build_meds_text(meds)
    if meds_text != "현재 복용 약 정보 없음":
        _append_rag_block(
            blocks,
            source="meds",
            title="현재 복용 약",
            content=meds_text,
        )
    return blocks


# RAG hook (MVP)
async def _build_rag_context(
    *,
    intent: str,
    latest_guide: Guide | None,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    profile: PatientProfile | None,
    kids_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    guide_blocks = extract_guide_blocks(latest_guide)
    profile_blocks = extract_profile_blocks(profile)
    schedule_blocks = extract_schedule_blocks(_build_schedule_text(schedules, meds))
    meds_blocks = extract_meds_blocks(_build_meds_text(meds))
    external_blocks = extract_external_blocks(
        mfds_evidence=[],
        kids_evidence=kids_evidence,
    )

    return build_rag_context(
        intent=intent,
        guide_blocks=guide_blocks,
        profile_blocks=profile_blocks,
        schedule_blocks=schedule_blocks,
        meds_blocks=meds_blocks,
        external_blocks=external_blocks,
        limit=8,
    )


# 컨텍스트 구성
async def _build_patient_chat_context(*, session_id: int, patient_id: int) -> PatientChatContext:
    profile = await _get_profile(patient_id)
    latest_guide = await _get_latest_done_guide(patient_id)
    meds = await _get_active_meds(patient_id)
    schedules = await _get_active_schedules(patient_id)
    recent_messages = (
        await ChatMessage.filter(session_id=session_id).order_by("-created_at", "-id").limit(CHAT_HISTORY_TURNS).all()
    )
    recent_messages = list(reversed(recent_messages))

    kids_evidence = await _build_kids_evidence(meds=meds, profile=profile)
    rag_context: list[dict[str, Any]] = []

    return PatientChatContext(
        patient_id=patient_id,
        profile=profile,
        latest_guide=latest_guide,
        meds=meds,
        schedules=schedules,
        recent_messages=recent_messages,
        kids_evidence=kids_evidence,
        rag_context=rag_context,
    )


# 질문 의도 판별
def _detect_intent(message: str) -> str:
    normalized = (message or "").strip()

    if any(k in normalized for k in _DAILY_CHAT_KEYWORDS):
        return "daily"
    if any(k in normalized for k in _PROFILE_SMOKING_KEYWORDS):
        return "profile_smoking"
    if any(k in normalized for k in _PROFILE_ALCOHOL_KEYWORDS):
        return "profile_alcohol"
    if any(k in normalized for k in _PROFILE_SLEEP_KEYWORDS):
        return "profile_sleep"
    if any(k in normalized for k in _PROFILE_EXERCISE_KEYWORDS):
        return "profile_exercise"
    if any(k in normalized for k in _SCHEDULE_KEYWORDS):
        return "schedule"
    if any(k in normalized for k in _MEDICATION_CAUTION_KEYWORDS):
        return "medication_caution"
    if "주의" in normalized and "약" in normalized:
        return "medication_caution"
    if any(k in normalized for k in _GUIDE_SUMMARY_KEYWORDS):
        return "guide"

    return "general"


# 보호자용 관리형 응답 변환
def _to_caregiver_style(*, answer: str, audience: str) -> str:
    lines = [
        "오늘 확인해보셔야 할 것:",
        f"- {answer}",
        "주의 신호:",
        "- 갑작스러운 증상 악화나 이상 반응이 보이면 의료진과 상담하기",
        "관리 포인트:",
        "- 복약 여부와 생활습관 기록을 함께 확인하기",
    ]

    if audience == "senior":
        lines.append("- 어지러움이나 보행 불안정이 있으면 낙상 위험을 함께 확인하기")

    return "\n".join(lines)


# 프로필 기반 직접 응답
def _answer_profile_intent(
    *,
    intent: str,
    profile: PatientProfile | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    if not profile:
        base = f"{target_label} 기준으로 등록된 건강 프로필이 없습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    if intent == "profile_smoking":
        value = getattr(profile, "avg_cig_packs_per_week", None)
        if value is None:
            base = f"{target_label} 기준으로 주간 흡연량 정보가 등록되어 있지 않습니다."
        else:
            base = f"{target_label} 기준으로 주에 평균 {value}갑 정도 흡연하는 것으로 기록되어 있습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    if intent == "profile_alcohol":
        value = getattr(profile, "avg_alcohol_bottles_per_week", None)
        if value is None:
            base = f"{target_label} 기준으로 주간 음주량 정보가 등록되어 있지 않습니다."
        else:
            base = f"{target_label} 기준으로 주에 평균 {value}병 정도 음주하는 것으로 기록되어 있습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    if intent == "profile_sleep":
        value = getattr(profile, "avg_sleep_hours_per_day", None)
        if value is None:
            base = f"{target_label} 기준으로 평균 수면 시간 정보가 등록되어 있지 않습니다."
        else:
            base = f"{target_label} 기준으로 하루 평균 {value}시간 정도 수면하는 것으로 기록되어 있습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    if intent == "profile_exercise":
        value = getattr(profile, "avg_exercise_minutes_per_day", None)
        if value is None:
            base = f"{target_label} 기준으로 평균 운동 시간 정보가 등록되어 있지 않습니다."
        else:
            base = f"{target_label} 기준으로 하루 평균 {value}분 정도 운동하는 것으로 기록되어 있습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    return None


# 스케줄 기반 직접 응답
def _answer_schedule_intent(
    *,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    schedule_text = _build_schedule_text(schedules, meds)
    if schedule_text == "등록된 복약 일정 없음":
        base = f"{target_label} 기준으로 등록된 복약 일정이 없습니다."
    else:
        base = f"{target_label} 기준 복약 일정은 다음과 같습니다.\n{schedule_text}"

    if audience == "senior":
        base += "\n어지러움이나 복약 시간 혼동이 생기지 않도록 복용 전 다시 확인하는 것이 좋습니다."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


# guide 기반 직접 응답
def _answer_guide_intent(
    *,
    guide: Guide | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    if not guide or not guide.content_text:
        return None

    base = f"{target_label} 기준 최신 가이드를 요약하면 다음과 같습니다.\n{guide.content_text}"

    if audience == "child":
        base += "\n어려운 부분은 보호자와 같이 확인하면 좋습니다."
    elif audience == "senior":
        base += "\n어지러움이나 낙상 위험이 있으면 복용 후 상태를 더 주의 깊게 살펴주세요."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_medication_caution_intent(
    *,
    guide: Guide | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    if not guide or not isinstance(guide.content_json, dict):
        return None

    sections = guide.content_json.get("sections") or []
    caution_body = ""

    for section in sections:
        title = str(section.get("title") or "")
        body = str(section.get("body") or "")
        if "주의" in title or "주의" in body or "신호" in title:
            caution_body = body
            break

    if not caution_body and guide.content_text:
        caution_body = guide.content_text

    if not caution_body:
        return None

    base = f"{target_label} 기준으로 특히 주의해서 볼 점은 다음과 같습니다.\n{caution_body}"

    if audience == "senior":
        base += "\n어지러움이 있으면 낙상 위험도 함께 조심해 주세요."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


# 일상 대화 응답
def _answer_daily_chat(
    *,
    message: str,
    requester_role: RequesterRole,
    target_label: str,
) -> str:
    normalized = (message or "").strip()

    if "이름이 뭐" in normalized or "너 이름" in normalized or "누구야" in normalized:
        return "저는 복약과 건강 정보를 도와드리는 의료 챗봇입니다."

    if "오늘 어때" in normalized or "오늘 하루" in normalized or "기분 어때" in normalized:
        return "저는 괜찮습니다. 오늘도 복약과 건강 관련 질문을 도와드릴 준비가 되어 있습니다."

    if "고마워" in normalized or "감사" in normalized:
        return "도움이 되었다면 다행입니다. 필요한 내용이 있으면 이어서 말씀해 주세요."

    if "안녕" in normalized or "반가워" in normalized:
        return f"안녕하세요. {target_label} 기준으로 복약과 건강 정보를 도와드릴게요."

    if "잘 자" in normalized:
        return "편안한 밤 보내세요. 복약 일정이 있다면 잊지 않도록 한 번 더 확인해 주세요."

    return (
        "일상적인 대화도 자연스럽게 도와드릴 수 있습니다. 의료 관련 내용은 기록된 정보 범위 안에서 안내드릴게요."
        if requester_role != RequesterRole.CAREGIVER
        else "일상적인 대화도 가능하지만, 보호자 관점에서는 복약과 상태 확인 중심으로 안내드릴 수 있습니다."
    )


# LLM 호출
async def _call_chat_model(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    model = (os.getenv("OPENAI_MODEL", "gpt-4o-mini") or "").strip()

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()
    return json.loads(content)


# 일반 fallback 답변
def _fallback_reply(
    *,
    latest_guide: Guide | None,
    meds_text: str,
    schedule_text: str,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    if latest_guide and latest_guide.content_text:
        base = (
            f"{target_label} 기준 최신 가이드를 참고해 안내드리면, {latest_guide.content_text} "
            f"추가로 궁금한 점을 더 구체적으로 말씀해 주세요."
        )
    else:
        base = (
            f"{target_label} 기준 최신 guide는 없지만, 현재 확인 가능한 약 정보는 다음과 같습니다.\n"
            f"{meds_text}\n복약 일정은 다음과 같습니다.\n{schedule_text}"
        )

    if audience == "senior":
        base += "\n어지러움이나 낙상 위험이 있는 경우 복용 후 상태를 함께 확인해 주세요."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


# assistant 응급 플래그 재구성
def _reconstruct_emergency_fields(*, current: ChatMessage, previous: ChatMessage | None) -> tuple[bool, str | None]:
    if current.role != "assistant":
        return False, None

    if previous and previous.role == "user":
        is_emergency, emergency_message = _detect_emergency(previous.content)
        if is_emergency:
            return True, emergency_message

    if "응급 상황이 의심됩니다" in current.content:
        return True, "응급 상황이 의심됩니다. 즉시 119 또는 가까운 응급실/의료기관에 연락해 주세요."

    return False, None


class ChatService:
    @staticmethod
    async def create_session(
        *,
        requester: User,
        patient_id: int,
        mode: str,
    ) -> ChatSessionCreateResponse:
        session = await ChatSession.create(
            user_id=int(requester.id),
            patient_id=patient_id,
            mode=mode,
        )

        return ChatSessionCreateResponse(
            success=True,
            data=ChatSessionCreateData(
                session_id=int(session.id),
                patient_id=patient_id,
                mode=mode,
                created_at=session.created_at,
            ),
        )

    @staticmethod
    async def list_messages(*, session_id: int) -> ChatMessageListResponse:
        session = await ChatSession.get_or_none(id=session_id)
        if not session:
            raise ChatServiceError(
                status_code=404,
                code="CHAT_SESSION_NOT_FOUND",
                message="채팅 세션을 찾을 수 없습니다.",
            )

        rows = await ChatMessage.filter(session_id=session_id).order_by("created_at", "id").all()

        items: list[ChatMessageItem] = []
        for idx, row in enumerate(rows):
            prev_row = rows[idx - 1] if idx > 0 else None
            is_emergency, emergency_message = _reconstruct_emergency_fields(
                current=row,
                previous=prev_row,
            )
            items.append(
                ChatMessageItem(
                    message_id=int(row.id),
                    role=row.role,
                    content=row.content,
                    is_emergency=is_emergency,
                    emergency_message=emergency_message,
                    disclaimer=CHAT_DISCLAIMER if row.role == "assistant" else None,
                    created_at=row.created_at,
                )
            )

        return ChatMessageListResponse(
            success=True,
            data=ChatMessageListData(
                session_id=int(session.id),
                items=items,
                total=len(items),
            ),
        )

    @staticmethod
    async def create_message(
        *,
        requester: User,
        session_id: int,
        content: str,
    ) -> ChatMessageCreateResponse:
        stripped = content.strip()
        if len(stripped) > CHAT_MAX_MESSAGE_CHARS:
            raise ChatServiceError(
                status_code=422,
                code="MESSAGE_TOO_LONG",
                message=f"메시지는 {CHAT_MAX_MESSAGE_CHARS}자 이하로 입력해 주세요.",
            )

        session = await ChatSession.get_or_none(id=session_id)
        if not session:
            raise ChatServiceError(
                status_code=404,
                code="CHAT_SESSION_NOT_FOUND",
                message="채팅 세션을 찾을 수 없습니다.",
            )

        patient_id = getattr(session, "patient_id", None)
        if patient_id is None:
            raise ChatServiceError(
                status_code=500,
                code="CHAT_SESSION_PATIENT_MISSING",
                message="세션에 연결된 환자 정보가 없습니다.",
            )

        requester_role = await _resolve_requester_role(int(requester.id))
        target_label = "선택한 복약자" if requester_role == RequesterRole.CAREGIVER else "회원님 기록"

        user_msg = await ChatMessage.create(
            session_id=session_id,
            role="user",
            content=stripped,
        )

        context = await _build_patient_chat_context(
            session_id=session_id,
            patient_id=int(patient_id),
        )

        audience = _resolve_audience(context.profile)
        is_emergency, emergency_message = _detect_emergency(stripped)
        intent = _detect_intent(stripped)

        context.rag_context = await _build_rag_context(
            intent=intent,
            latest_guide=context.latest_guide,
            meds=context.meds,
            schedules=context.schedules,
            profile=context.profile,
            kids_evidence=context.kids_evidence,
        )

        if is_emergency:
            assistant_content = f"{emergency_message} 현재 질문은 즉시 전문 의료진 확인이 우선입니다."
        else:
            deterministic_answer: str | None = None

            if intent in {"profile_smoking", "profile_alcohol", "profile_sleep", "profile_exercise"}:
                deterministic_answer = _answer_profile_intent(
                    intent=intent,
                    profile=context.profile,
                    target_label=target_label,
                    requester_role=requester_role,
                    audience=audience,
                )
            elif intent == "schedule":
                deterministic_answer = _answer_schedule_intent(
                    meds=context.meds,
                    schedules=context.schedules,
                    target_label=target_label,
                    requester_role=requester_role,
                    audience=audience,
                )
            elif intent == "medication_caution":
                deterministic_answer = _answer_medication_caution_intent(
                    guide=context.latest_guide,
                    target_label=target_label,
                    requester_role=requester_role,
                    audience=audience,
                )
            elif intent == "guide":
                deterministic_answer = _answer_guide_intent(
                    guide=context.latest_guide,
                    target_label=target_label,
                    requester_role=requester_role,
                    audience=audience,
                )
            elif intent == "daily":
                deterministic_answer = _answer_daily_chat(
                    message=stripped,
                    requester_role=requester_role,
                    target_label=target_label,
                )

            if deterministic_answer:
                assistant_content = deterministic_answer
            else:
                meds_text = _build_meds_text(context.meds)
                schedule_text = _build_schedule_text(context.schedules, context.meds)
                profile_text = _build_profile_text(context.profile)
                guide_text = _build_guide_text(context.latest_guide)
                history_text = _build_history_text(context.recent_messages)
                kids_text = _build_kids_text(context.kids_evidence)
                rag_text = _build_rag_text(context.rag_context)

                try:
                    system_prompt = _read_prompt_template("chat_system_prompt.txt").format(
                        requester_role=requester_role.value,
                        target_label=target_label,
                        audience_label=_audience_label(audience),
                        extra_safety=_extra_safety_text(audience),
                        kids_text=kids_text,
                        rag_text=rag_text,
                        disclaimer=CHAT_DISCLAIMER,
                    )
                    user_prompt = _read_prompt_template("chat_user_prompt.txt").format(
                        guide_text=guide_text,
                        meds_text=meds_text,
                        schedule_text=schedule_text,
                        profile_text=profile_text,
                        history_text=history_text,
                        user_message=stripped,
                    )
                    llm_result = await _call_chat_model(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )
                    assistant_content = (llm_result.get("content") or "").strip()
                    if not assistant_content:
                        raise ValueError("empty assistant content")
                    is_emergency = bool(llm_result.get("is_emergency", False))
                    emergency_message = llm_result.get("emergency_message")
                except Exception:
                    logger.exception("chat fallback used session_id=%s", session_id)
                    assistant_content = _fallback_reply(
                        latest_guide=context.latest_guide,
                        meds_text=meds_text,
                        schedule_text=schedule_text,
                        target_label=target_label,
                        requester_role=requester_role,
                        audience=audience,
                    )

        assistant_msg = await ChatMessage.create(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
        )

        return ChatMessageCreateResponse(
            success=True,
            data=ChatMessageCreateData(
                session_id=int(session.id),
                user_message=ChatMessageItem(
                    message_id=int(user_msg.id),
                    role="user",
                    content=user_msg.content,
                    is_emergency=False,
                    emergency_message=None,
                    disclaimer=None,
                    created_at=user_msg.created_at,
                ),
                assistant_message=ChatMessageItem(
                    message_id=int(assistant_msg.id),
                    role="assistant",
                    content=assistant_msg.content,
                    is_emergency=is_emergency,
                    emergency_message=emergency_message,
                    disclaimer=CHAT_DISCLAIMER,
                    created_at=assistant_msg.created_at,
                ),
            ),
        )
