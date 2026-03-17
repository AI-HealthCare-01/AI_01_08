from __future__ import annotations

import json
import logging
import os
import re
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
from app.models.patients import Patient, PatientProfile
from app.models.schedules import MedSchedule, MedScheduleTime
from app.models.users import User
from app.services.kids_client import KIDSClient
from app.services.mfds import MfdsService
from app.services.role_utils import user_has_role
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
    "숨쉬기가 힘들",
    "숨을 쉬기 힘들",
    "숨 못 쉬",
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
_DIRECT_EMERGENCY_SYMPTOM_KEYWORDS = [
    "숨이 차",
    "호흡곤란",
    "숨쉬기 힘들",
    "숨쉬기가 힘들",
    "숨을 쉬기 힘들",
    "숨 못 쉬",
    "가슴 통증",
    "의식이 흐려",
    "실신",
    "경련",
    "피가 나",
    "출혈",
    "극심한 통증",
]
_EMERGENCY_EXPLORATION_KEYWORDS = [
    "119를 생각",
    "119를 불러",
    "119에 연락",
    "병원이나 119",
    "응급으로 봐야",
    "응급 신호",
    "응급 상황인지",
    "위험하면",
    "기준으로",
    "어떤 증상",
]

_PROFILE_SMOKING_KEYWORDS = ["담배", "흡연", "몇 갑", "주에 평균", "주간 흡연"]
_PROFILE_ALCOHOL_KEYWORDS = ["술", "음주", "몇 병", "주간 음주"]
_PROFILE_SLEEP_KEYWORDS = ["수면", "잠", "몇 시간"]
_PROFILE_EXERCISE_KEYWORDS = ["운동", "몇 분", "운동량"]
_SCHEDULE_KEYWORDS = ["복약스케줄", "복약 스케줄", "언제 먹", "언제 복용", "몇 시", "스케줄", "일정"]
_GUIDE_SUMMARY_KEYWORDS = ["전반적", "가이드", "약 설명", "무슨 약"]
_MED_LIST_KEYWORDS = [
    "복용하고있는 약",
    "복용하고 있는 약",
    "먹고 있는 약",
    "내가 먹는 약",
    "먹는 약",
    "먹어야 할 약",
    "먹어야 하는 약",
    "복용해야 할 약",
    "복용해야 하는 약",
    "현재 약",
    "약 목록",
    "무슨 약을",
]
_MED_TIME_SPLIT_KEYWORDS = [
    "아침, 저녁",
    "아침, 저녁으로",
    "아침 저녁",
    "아침 저녁으로",
    "아침과 저녁",
    "아침/저녁",
    "나눠서",
    "구분해서",
    "언제 먹는 약",
]
_MED_REGULARITY_KEYWORDS = ["매일 먹는 약", "매일 먹어야", "꼭 매일", "정해진 시간에 먹는 약", "매일 복용"]
_PRN_KEYWORDS = ["매일 먹는 약이야", "열날 때만", "열 날 때만", "필요할 때만", "필요 시", "매일 먹어야 해"]
_CAREGIVER_CHECK_KEYWORDS = [
    "보호자가 꼭 확인",
    "보호자가 확인",
    "오늘 확인해야",
    "꼭 확인해야 할 것",
    "체크리스트",
    "관리 포인트",
    "체크포인트",
    "오늘 복약에서",
]
_ALLERGY_FOOD_KEYWORDS = [
    "알레르기",
    "음식으로 조심",
    "음식 조심",
    "먹지 않도록",
    "음식으로 특히",
    "조심해야 하는 음식",
    "음식으로 특히 조심",
    "먹으면 안",
]
_MISSED_DOSE_KEYWORDS = [
    "놓쳤다면",
    "놓쳤으면",
    "놓쳤고",
    "놓쳤는데",
    "복약을 놓쳤",
    "지금 바로 먹여",
    "바로 먹여도",
    "깜빡",
    "복용을 놓쳤",
]
_LIFESTYLE_TOP_KEYWORDS = [
    "생활관리",
    "생활 관리",
    "생활관리에서",
    "생활 관리에서",
    "생활관리 요약",
    "생활 관리 요약",
    "중요한 것 3가지",
    "중요한 것 세 가지",
    "중요한 것만 3가지",
    "세 가지만",
    "세 가지",
    "3가지만",
    "3가지",
]
_SESSION_SUMMARY_KEYWORDS = ["한 줄로 요약", "지금까지 대화", "상태를 요약", "요약해줘"]
_EMERGENCY_GUIDANCE_KEYWORDS = [
    "119를 생각",
    "119에 연락",
    "병원이나 119",
    "응급으로 봐야",
    "응급 신호",
    "어떤 증상",
    "위험하면",
    "병원 가야",
]
_RASH_KEYWORDS = ["두드러기", "발진", "두드러기처럼", "발진이 생기", "약 먹고 나서 발진"]
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
    "너 뭐해",
    "뭘 하는",
    "뭐 하는 애",
    "뭐하는 애",
    "뭐하는 애니",
    "잘 자",
    "좋은 아침",
]
_BOT_CAPABILITY_KEYWORDS = [
    "뭘 할 수",
    "무엇을 할 수",
    "뭐 도와줄 수",
    "어떤 걸 도와줄 수",
    "어떤걸 도와줄 수",
    "무엇을 도와줄 수",
    "뭘 도와줄 수",
    "도와줄 수 있어",
    "어떤 질문",
    "어떤 걸 물어",
    "무엇을 물어",
]
_MED_DETAIL_KEYWORDS = ["어떤 약", "무슨 약", "뭐하는 약", "설명해줘", "설명해 줘", "약 설명"]
_FOLLOWUP_MED_REFERENCES = ["그 약", "이 약", "그거", "이거", "저 약", "해당 약"]
_GENERAL_CAUTION_KEYWORDS = ["주의", "조심", "주의할 게", "조심할 게", "주의해야", "조심해야", "주의해", "조심해"]
_CONDITION_TREATMENT_KEYWORDS = [
    "좋은약",
    "좋은 약",
    "어떤 약",
    "무슨 약",
    "치료약",
    "치료 약",
    "도움 되는 약",
    "도움되는 약",
]
_EXTERNAL_MED_FOLLOWUP_KEYWORDS = [
    "혹시 아나",
    "아나해서",
    "아나 해서",
    "알아?",
    "알아",
    "궁금해",
    "궁금해서",
    "처방받은 약은 아닌데",
    "처방받은약은아닌데",
]
_EXTERNAL_DRUG_STOPWORDS = {
    "아이",
    "내",
    "내가",
    "기록",
    "기록에는",
    "없는",
    "약인데",
    "독감",
    "감기",
    "치료",
    "치료로",
    "자주",
    "듣는",
    "새로",
    "처방",
    "처방받은",
    "처방받을",
    "수도",
    "있는데",
    "주의",
    "주의할",
    "특히",
    "같이",
    "복용",
    "부작용",
    "용도",
    "주의사항",
    "약",
}
_EXTERNAL_DRUG_SUFFIXES = ["정", "시럽", "캡슐", "현탁액", "산", "주사", "크림", "패치", "정제", "액", "연질캡슐"]
_EXTERNAL_DRUG_CONTEXT_KEYWORDS = ["용도", "부작용", "주의사항", "정보", "처방", "감기", "독감"]


def _compact_text(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isalnum() or ("가" <= ch <= "힣"))


def _contains_keyword(message: str, keyword: str) -> bool:
    original = str(message or "").strip()
    if keyword in original:
        return True
    return _compact_text(keyword) in _compact_text(original)


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(_contains_keyword(message, keyword) for keyword in keywords)


def _split_text_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    raw = str(value or "").strip()
    if not raw:
        return []

    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass

    return [
        item.strip().strip('"').strip("'") for chunk in raw.splitlines() for item in chunk.split(",") if item.strip()
    ]


def _append_unique(items: list[str], value: str | None) -> None:
    clean = str(value or "").strip()
    if clean and clean not in items:
        items.append(clean)


def _first_clean_line(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for line in raw.splitlines():
        clean = line.strip().lstrip("-").strip()
        if clean:
            return clean
    return raw


def _summarize_text(value: str | None, *, max_sentences: int = 2) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    compact = re.sub(r"\s+", " ", raw)
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+|(?<=다\.)\s*", compact) if item.strip()]
    if not sentences:
        return compact
    return " ".join(sentences[:max_sentences]).strip()


def _dedupe_lines(items: list[str], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        clean = str(item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        results.append(clean)
        if limit is not None and len(results) >= limit:
            break
    return results


def _choose_korean_particle(word: str, pair: tuple[str, str]) -> str:
    text = str(word or "").strip()
    if not text:
        return pair[1]
    last = text[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        has_batchim = (code - 0xAC00) % 28 != 0
        return pair[0] if has_batchim else pair[1]
    return pair[1]


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


@dataclass
class QuestionAnalysis:
    raw_message: str
    intents: list[str]
    primary_intent: str
    target_med: dict[str, Any] | None
    external_drug_name: str | None
    is_emergency: bool
    emergency_message: str | None
    answer_mode: str


# 요청자 역할 판별
async def _resolve_requester_role(user_id: int) -> RequesterRole:
    # Louis수정(코드삭제): Patient row 존재 여부만으로 역할을 판별하면 보호자+본인프로필 계정이 PATIENT로 오인됨
    if await user_has_role(user_id, "ADMIN"):
        return RequesterRole.ADMIN

    # Louis수정(기능추가): 역할 테이블 기준으로 우선 판별해 보호자가 연동 환자에 정상 접근하도록 수정
    if await user_has_role(user_id, "CAREGIVER", "GUARDIAN"):
        return RequesterRole.CAREGIVER

    if await user_has_role(user_id, "PATIENT"):
        return RequesterRole.PATIENT

    patient_exists = await Patient.filter(user_id=user_id).exists()
    if patient_exists:
        return RequesterRole.PATIENT

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
    if _contains_any(normalized, _DIRECT_EMERGENCY_SYMPTOM_KEYWORDS):
        return (
            True,
            "응급 상황이 의심됩니다. 즉시 119 또는 가까운 응급실/의료기관에 연락해 주세요.",
        )

    if _contains_any(normalized, ["119", "응급실", "응급"]) and _contains_any(
        normalized, _EMERGENCY_EXPLORATION_KEYWORDS
    ):
        return False, None

    for keyword in ["응급실", "119"]:
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
    upper_normalized = normalized.upper()
    if normalized in {"1,2,3,4,5,6,7", "1,2,3,4,5,6,7,"} or upper_normalized in {
        "MON,TUE,WED,THU,FRI,SAT,SUN",
        "MON,TUE,WED,THU,FRI,SAT,SUN,",
    }:
        return "매일"

    day_map = {
        "1": "월",
        "2": "화",
        "3": "수",
        "4": "목",
        "5": "금",
        "6": "토",
        "7": "일",
        "MON": "월",
        "TUE": "화",
        "WED": "수",
        "THU": "목",
        "FRI": "금",
        "SAT": "토",
        "SUN": "일",
        "월": "월",
        "화": "화",
        "수": "수",
        "목": "목",
        "금": "금",
        "토": "토",
        "일": "일",
    }
    items = [day_map.get(x.upper(), day_map.get(x, x)) for x in normalized.split(",") if x]
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
                "notes": row.notes,
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
    return _analyze_intents(message)[0]


def _analyze_intents(message: str) -> list[str]:
    normalized = (message or "").strip()
    intents: list[str] = []
    external_drug_name = _extract_external_drug_name(normalized, None)

    if _contains_any(normalized, _DAILY_CHAT_KEYWORDS):
        _append_unique(intents, "daily")
    if _contains_any(normalized, _BOT_CAPABILITY_KEYWORDS):
        _append_unique(intents, "daily")
    if _contains_any(normalized, ["두드러기", "발진"]) and _contains_any(normalized, ["약 먹고", "복용", "약 먹은 뒤"]):
        _append_unique(intents, "rash")
    if _contains_any(normalized, _RASH_KEYWORDS):
        _append_unique(intents, "rash")
    if _contains_any(normalized, _MED_DETAIL_KEYWORDS) and _contains_any(
        normalized, ["언제 먹", "언제 복용", "몇 시", "시간"]
    ):
        _append_unique(intents, "med_detail")
    if _contains_any(normalized, _PROFILE_SMOKING_KEYWORDS):
        _append_unique(intents, "profile_smoking")
    if _contains_any(normalized, _PROFILE_ALCOHOL_KEYWORDS):
        _append_unique(intents, "profile_alcohol")
    if _contains_any(normalized, _PROFILE_SLEEP_KEYWORDS):
        _append_unique(intents, "profile_sleep")
    if _contains_any(normalized, _PROFILE_EXERCISE_KEYWORDS):
        _append_unique(intents, "profile_exercise")
    if (
        _contains_any(normalized, ["아침", "오전"])
        and _contains_any(normalized, ["저녁", "오후", "취침 전"])
        and _contains_any(normalized, ["나눠", "구분"])
    ):
        _append_unique(intents, "med_time_split")
    if _contains_any(normalized, _MED_TIME_SPLIT_KEYWORDS):
        _append_unique(intents, "med_time_split")
    if _contains_any(normalized, _MED_REGULARITY_KEYWORDS):
        _append_unique(intents, "med_regularity")
    if _contains_any(normalized, _PRN_KEYWORDS):
        _append_unique(intents, "med_prn")
    if _contains_any(normalized, _MED_DETAIL_KEYWORDS):
        _append_unique(intents, "med_detail")
    if _contains_any(normalized, _CONDITION_TREATMENT_KEYWORDS) and "external_med" not in intents:
        _append_unique(intents, "condition_general")
    if external_drug_name or _contains_any(
        normalized, ["약에 대해서 궁금", "라는 약", "라고 알아", "약 알아", "약이 궁금"]
    ):
        _append_unique(intents, "external_med")
    if _contains_any(normalized, ["같이", "상호작용", "함께"]) and _contains_any(
        normalized, _MEDICATION_CAUTION_KEYWORDS
    ):
        _append_unique(intents, "medication_caution")
    if _contains_any(normalized, ["음식", "알레르기"]) and _contains_any(normalized, ["조심", "주의"]):
        _append_unique(intents, "allergy_food")
    if _contains_any(normalized, _MED_LIST_KEYWORDS):
        _append_unique(intents, "med_list")
    if _contains_any(normalized, _SCHEDULE_KEYWORDS):
        _append_unique(intents, "schedule")
    if _contains_any(normalized, _CAREGIVER_CHECK_KEYWORDS):
        _append_unique(intents, "caregiver_check")
    if _contains_any(normalized, _ALLERGY_FOOD_KEYWORDS):
        _append_unique(intents, "allergy_food")
    if _contains_any(normalized, _MISSED_DOSE_KEYWORDS):
        _append_unique(intents, "missed_dose")
    if _contains_any(normalized, _EMERGENCY_GUIDANCE_KEYWORDS):
        _append_unique(intents, "emergency_guidance")
    if _contains_any(normalized, ["3가지만", "세 가지만"]) and _contains_any(normalized, ["생활"]):
        _append_unique(intents, "lifestyle_top")
    if _contains_any(normalized, _LIFESTYLE_TOP_KEYWORDS):
        _append_unique(intents, "lifestyle_top")
    if _contains_any(normalized, _SESSION_SUMMARY_KEYWORDS):
        _append_unique(intents, "session_summary")
    if _contains_any(normalized, _MEDICATION_CAUTION_KEYWORDS):
        _append_unique(intents, "medication_caution")
    if _contains_any(normalized, ["주의"]) and _contains_any(normalized, ["약"]):
        _append_unique(intents, "medication_caution")
    if _contains_any(normalized, _GENERAL_CAUTION_KEYWORDS):
        _append_unique(intents, "general_caution")
    if _contains_any(normalized, _GUIDE_SUMMARY_KEYWORDS):
        _append_unique(intents, "guide")

    return intents or ["general"]


def _resolve_answer_mode(*, intents: list[str], is_emergency: bool) -> str:
    if is_emergency:
        return "emergency"
    if "external_med" in intents:
        return "external_drug_counseling"
    if "condition_general" in intents:
        return "condition_counseling"
    if "daily" in intents:
        return "daily_chat"
    if any(intent in intents for intent in {"missed_dose", "emergency_guidance", "rash"}):
        return "safety_guidance"
    if len(intents) == 1 and intents[0] in {
        "profile_smoking",
        "profile_alcohol",
        "profile_sleep",
        "profile_exercise",
        "med_list",
        "med_time_split",
        "med_regularity",
        "schedule",
        "session_summary",
    }:
        return "direct_fact"
    if any(
        intent in intents for intent in {"caregiver_check", "self_check", "lifestyle_top", "general_caution", "guide"}
    ):
        return "record_counseling"
    return "general_counseling"


def _analyze_question(
    *,
    message: str,
    meds: list[dict[str, Any]],
    recent_messages: list[ChatMessage],
    requester_role: RequesterRole,
) -> QuestionAnalysis:
    normalized = (message or "").strip()
    external_drug_name = _extract_external_drug_name(normalized, recent_messages)
    raw_intents = _analyze_intents(normalized)
    if external_drug_name and "external_med" not in raw_intents:
        raw_intents.append("external_med")

    intents = _normalize_intent_order(raw_intents, requester_role)
    target_med = _extract_target_med(
        message=normalized,
        meds=meds,
        recent_messages=recent_messages,
    )
    is_emergency, emergency_message = _detect_emergency(normalized)
    answer_mode = _resolve_answer_mode(intents=intents, is_emergency=is_emergency)

    return QuestionAnalysis(
        raw_message=normalized,
        intents=intents,
        primary_intent=intents[0],
        target_med=target_med,
        external_drug_name=external_drug_name,
        is_emergency=is_emergency,
        emergency_message=emergency_message,
        answer_mode=answer_mode,
    )


# 보호자용 관리형 응답 변환
def _to_caregiver_style(*, answer: str, audience: str) -> str:
    lines = [
        "먼저 확인할 내용:",
        f"- {answer}",
        "위험 신호:",
        "- 갑작스러운 증상 악화나 이상 반응이 보이면 의료진과 상담하기",
        "함께 볼 점:",
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


# 현재 복용 약 목록 직접 응답
def _answer_med_list_intent(
    *,
    meds: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    if not meds:
        base = f"{target_label} 기준으로 현재 확인되는 복용 약 정보가 없습니다."
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    med_lines: list[str] = []
    for med in meds:
        name = med.get("display_name") or "약 이름 없음"
        dosage = med.get("dosage")
        notes = med.get("notes")
        chunk = name
        if dosage:
            chunk += f" {dosage}"
        if notes:
            chunk += f" ({notes})"
        med_lines.append(f"- {chunk}")

    base = f"{target_label} 기준으로 현재 복용 중인 약은 다음과 같습니다.\n" + "\n".join(med_lines)
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _extract_target_med(
    *,
    message: str,
    meds: list[dict[str, Any]],
    recent_messages: list[ChatMessage] | None = None,
) -> dict[str, Any] | None:
    normalized = (message or "").strip()
    for med in meds:
        name = str(med.get("display_name") or "").strip()
        if name and _contains_keyword(normalized, name):
            return med

    if recent_messages and _contains_any(normalized, _FOLLOWUP_MED_REFERENCES):
        for recent in reversed(recent_messages):
            recent_content = str(getattr(recent, "content", "") or "")
            for med in meds:
                name = str(med.get("display_name") or "").strip()
                if name and _contains_keyword(recent_content, name):
                    return med

    if len(meds) == 1:
        return meds[0]
    return None


def _extract_external_drug_name(message: str, recent_messages: list[ChatMessage] | None = None) -> str | None:
    normalized = str(message or "").strip()
    patterns = [
        r"([가-힣A-Za-z0-9]+)라고\s*알아",
        r"([가-힣A-Za-z0-9]+)라는\s*약",
        r"([가-힣A-Za-z0-9]+)은\s*어떤\s*약",
        r"([가-힣A-Za-z0-9]+)[이가은는]\s*무슨\s*약",
        r"([가-힣A-Za-z0-9]+)[이가은는]\s*어떤\s*약",
        r"([가-힣A-Za-z0-9]+)의\s*(용도|주의사항|부작용)",
        r"([가-힣A-Za-z0-9]+)[를을은는이가]\s*(새로\s*처방|처방받|먹는\s*약|용도|부작용|주의사항)",
        r"([가-힣A-Za-z0-9]+)\s*정보좀",
        r"([가-힣A-Za-z0-9]+)\s*정보\s*좀",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate not in _EXTERNAL_DRUG_STOPWORDS:
                return candidate

    if _contains_any(normalized, _EXTERNAL_DRUG_CONTEXT_KEYWORDS):
        tokens = [token.strip() for token in re.split(r"[\s,./()]+", normalized) if token.strip()]
        preferred: list[str] = []
        fallback: list[str] = []
        for token in tokens:
            if token in _EXTERNAL_DRUG_STOPWORDS:
                continue
            if len(token) < 2:
                continue
            if _contains_any(token, _EXTERNAL_DRUG_CONTEXT_KEYWORDS):
                continue
            if any(ch.isdigit() for ch in token):
                continue
            if any(token.endswith(suffix) for suffix in _EXTERNAL_DRUG_SUFFIXES):
                preferred.append(token)
            else:
                fallback.append(token)
        if preferred:
            return preferred[0]
        if fallback:
            return fallback[0]

    if recent_messages and _contains_any(normalized, _EXTERNAL_MED_FOLLOWUP_KEYWORDS):
        for recent in reversed(recent_messages):
            recent_content = str(getattr(recent, "content", "") or "").strip()
            for pattern in patterns:
                match = re.search(pattern, recent_content)
                if match:
                    candidate = match.group(1).strip()
                    if candidate and candidate not in _EXTERNAL_DRUG_STOPWORDS:
                        return candidate
            if _contains_any(recent_content, _EXTERNAL_DRUG_CONTEXT_KEYWORDS):
                tokens = [token.strip() for token in re.split(r"[\s,./()]+", recent_content) if token.strip()]
                preferred: list[str] = []
                fallback: list[str] = []
                for token in tokens:
                    if token in _EXTERNAL_DRUG_STOPWORDS or len(token) < 2 or any(ch.isdigit() for ch in token):
                        continue
                    if _contains_any(token, _EXTERNAL_DRUG_CONTEXT_KEYWORDS):
                        continue
                    if any(token.endswith(suffix) for suffix in _EXTERNAL_DRUG_SUFFIXES):
                        preferred.append(token)
                    else:
                        fallback.append(token)
                if preferred:
                    return preferred[0]
                if fallback:
                    return fallback[0]
    return None


async def _lookup_external_med_info(drug_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {"mfds": None, "kids": []}
    mfds_service = MfdsService()
    kids_client = KIDSClient()
    normalized_query = _compact_text(drug_name).lower()

    try:
        mfds_response = await mfds_service.search_easy_drug_info(drug_name=drug_name, num_of_rows=1)
        if mfds_response.items:
            for item in mfds_response.items:
                item_name = _compact_text(getattr(item, "item_name", "")).lower()
                if normalized_query and item_name and (normalized_query in item_name or item_name in normalized_query):
                    result["mfds"] = item
                    break
    except Exception:
        logger.exception("external med mfds lookup failed drug=%s", drug_name)

    try:
        if kids_client.is_enabled():
            kids_items = await kids_client.search_safety_evidence(drug_name)
            filtered_kids: list[dict[str, Any]] = []
            for item in kids_items:
                content = _compact_text(str(item.get("content") or "")).lower()
                if normalized_query and content and normalized_query in content:
                    filtered_kids.append(item)
            result["kids"] = filtered_kids[:5]
    except Exception:
        logger.exception("external med kids lookup failed drug=%s", drug_name)

    return result


def _build_external_drug_text(*, drug_name: str | None, lookup: dict[str, Any] | None) -> str:
    clean_name = str(drug_name or "").strip()
    if not clean_name:
        return "질문 관련 외부 약 정보 없음"

    if not lookup:
        return f"- 질문한 외부 약 이름: {clean_name}"

    mfds_item = lookup.get("mfds")
    kids_items = lookup.get("kids") or []
    parts = [f"- 질문한 외부 약 이름: {clean_name}"]

    if mfds_item:
        item_name = str(getattr(mfds_item, "item_name", "") or clean_name).strip()
        efficacy = _first_clean_line(getattr(mfds_item, "efficacy", None))
        precautions = _first_clean_line(getattr(mfds_item, "precautions", None))
        dosage_info = _first_clean_line(getattr(mfds_item, "dosage_info", None))
        if item_name:
            parts.append(f"- MFDS 약 이름: {item_name}")
        if efficacy:
            parts.append(f"- MFDS 용도: {efficacy}")
        if precautions:
            parts.append(f"- MFDS 주의사항: {precautions}")
        if dosage_info:
            parts.append(f"- MFDS 복용 참고: {dosage_info}")

    if kids_items:
        first_kids = _first_clean_line(kids_items[0].get("content"))
        if first_kids:
            parts.append(f"- KIDS 안전 근거: {first_kids}")

    if len(parts) == 1:
        parts.append("- 외부 의약 정보 근거는 아직 직접 확인되지 않았습니다.")

    return "\n".join(parts)


def _should_prefer_llm(*, analysis: QuestionAnalysis) -> bool:
    return analysis.answer_mode in {
        "external_drug_counseling",
        "condition_counseling",
        "record_counseling",
        "general_counseling",
        "daily_chat",
    }


def _answer_med_time_split_intent(
    *,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    med_name_map = {int(med.get("patient_med_id")): med for med in meds if med.get("patient_med_id") is not None}
    morning: list[str] = []
    evening: list[str] = []
    other: list[str] = []

    for schedule in schedules:
        patient_med_id = int(schedule.get("patient_med_id"))
        med = med_name_map.get(patient_med_id, {})
        label = med.get("display_name") or f"약 #{patient_med_id}"
        dosage = med.get("dosage")
        notes = str(med.get("notes") or "").strip()
        shown = f"{label} {dosage}".strip()
        if any(keyword in notes for keyword in ["필요", "열날", "증상", "통증 시"]):
            other.append(f"{shown} (필요 시 복용)")
            continue
        times = schedule.get("times") or []
        if not times:
            other.append(shown)
            continue
        for item in times:
            time_of_day = str(item.get("time_of_day") or "")
            hour = int(time_of_day.split(":")[0]) if ":" in time_of_day else -1
            if 4 <= hour < 12:
                morning.append(shown)
            elif 17 <= hour <= 23:
                evening.append(shown)
            else:
                other.append(f"{shown} ({_humanize_time(time_of_day)})")

    parts = [f"{target_label} 기준으로 복약 시간을 나누면 다음과 같습니다."]
    if morning:
        parts.append("아침:")
        parts.extend(f"- {item}" for item in list(dict.fromkeys(morning)))
    if evening:
        parts.append("저녁:")
        parts.extend(f"- {item}" for item in list(dict.fromkeys(evening)))
    if other:
        parts.append("기타 시간:")
        parts.extend(f"- {item}" for item in list(dict.fromkeys(other)))
    if len(parts) == 1:
        parts.append("- 등록된 복약 일정 정보가 충분하지 않습니다.")

    base = "\n".join(parts)
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_med_regularity_intent(
    *,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    schedule_med_ids = {schedule.get("patient_med_id") for schedule in schedules}
    lines: list[str] = []
    for med in meds:
        name = str(med.get("display_name") or "해당 약").strip()
        notes = str(med.get("notes") or "").strip()
        patient_med_id = med.get("patient_med_id")
        if any(keyword in notes for keyword in ["필요", "열날", "증상", "통증 시"]):
            lines.append(f"- {name}: 필요 시 복용으로 보는 것이 자연스럽습니다.")
        elif patient_med_id in schedule_med_ids or any(
            keyword in notes for keyword in ["식후 복용", "취침 전", "기상 직후", "아침", "저녁"]
        ):
            lines.append(f"- {name}: 기록상 매일 정해진 시점에 복용하는 약으로 보입니다.")
        else:
            lines.append(f"- {name}: 현재 정보만으로 매일 복용 여부를 단정하기는 어렵습니다.")

    base = f"{target_label} 기준으로 매일 복용 여부를 보면 다음과 같습니다.\n" + "\n".join(lines)
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_med_prn_intent(
    *,
    message: str,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    recent_messages: list[ChatMessage] | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    matched = _extract_target_med(message=message, meds=meds, recent_messages=recent_messages)

    if not matched:
        return None

    notes = str(matched.get("notes") or "").strip()
    name = matched.get("display_name") or "이 약"
    patient_med_id = matched.get("patient_med_id")
    matched_schedules = [schedule for schedule in schedules if schedule.get("patient_med_id") == patient_med_id]

    if any(keyword in notes for keyword in ["필요", "열날", "증상", "통증 시"]):
        base = f"{target_label} 기준으로 {name}은 매일 정해진 시간에 먹는 약이라기보다 증상이 있을 때 복용하는 약으로 보는 것이 더 자연스럽습니다."
    elif matched_schedules or any(
        keyword in notes for keyword in ["식후 복용", "취침 전", "기상 직후", "아침", "저녁"]
    ):
        times: list[str] = []
        for schedule in matched_schedules:
            for item in schedule.get("times") or []:
                time_label = _humanize_time(item.get("time_of_day"))
                if time_label not in times:
                    times.append(time_label)
        if times:
            base = f"{target_label} 기준으로 {name}은 기록상 매일 복용하는 약으로 보는 것이 자연스럽습니다. 현재 등록된 시간은 {', '.join(times[:3])}입니다."
        else:
            base = f"{target_label} 기준으로 {name}은 메모와 일정상 매일 정해진 시점에 복용하는 약으로 보는 것이 자연스럽습니다."
    elif notes:
        base = f"{target_label} 기준으로 {name}은 메모상 `{notes}`로 기록되어 있습니다. 정시 복용 여부는 처방 의도와 문서 내용을 함께 확인하는 것이 좋습니다."
    else:
        base = f"{target_label} 기준으로 {name}의 매일 복용 여부를 단정할 근거는 부족합니다. 확정 문서와 처방 지시를 함께 확인해 주세요."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


async def _answer_med_detail_intent(
    *,
    message: str,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    recent_messages: list[ChatMessage] | None,
    matched_med: dict[str, Any] | None = None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    matched = matched_med or _extract_target_med(message=message, meds=meds, recent_messages=recent_messages)
    if not matched:
        return None

    name = str(matched.get("display_name") or "해당 약").strip()
    dosage = str(matched.get("dosage") or "").strip()
    notes = str(matched.get("notes") or "").strip()
    patient_med_id = matched.get("patient_med_id")

    schedule_lines: list[str] = []
    for schedule in schedules:
        if schedule.get("patient_med_id") != patient_med_id:
            continue
        for item in schedule.get("times") or []:
            time_label = _humanize_time(item.get("time_of_day"))
            days_label = _humanize_days(item.get("days_of_week"))
            schedule_lines.append(f"{days_label} {time_label}".strip())

    lookup = await _lookup_external_med_info(name)
    mfds_item = lookup.get("mfds")
    kids_items = lookup.get("kids") or []

    parts = [f"{target_label} 기준으로 {name} 정보는 다음과 같습니다."]
    efficacy = _first_clean_line(getattr(mfds_item, "efficacy", None)) if mfds_item else ""
    if dosage:
        parts.append(f"- 용량: {dosage}")
    if efficacy:
        parts.append(f"- 용도: {efficacy}")
    if schedule_lines:
        parts.append("- 복용 시간: " + ", ".join(schedule_lines[:3]))
    if notes:
        parts.append(f"- 복용 메모: {notes}")
    precautions = _first_clean_line(getattr(mfds_item, "precautions", None)) if mfds_item else ""
    if precautions:
        parts.append(f"- 주의사항: {precautions}")
    if kids_items:
        kids_summary = _first_clean_line(kids_items[0].get("content"))
        if kids_summary:
            parts.append(f"- 추가 안전 근거: {kids_summary}")

    base = "\n".join(parts)
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


# 보호자 체크포인트 직접 응답
def _answer_caregiver_check_intent(
    *,
    guide: Guide | None,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    points: list[str] = []

    if guide and isinstance(guide.caregiver_summary, dict):
        for key in ("today_checklist", "care_points", "warning_signs"):
            value = guide.caregiver_summary.get(key) or []
            if isinstance(value, list):
                points.extend(str(item).strip() for item in value if str(item).strip())

    if not points and schedules:
        schedule_text = _build_schedule_text(schedules, meds)
        points.append(f"오늘 복약 일정 확인: {schedule_text}")

    if not points:
        base = f"{target_label} 기준으로 오늘 보호자가 확인할 체크포인트 정보가 아직 충분하지 않습니다."
    else:
        deduped: list[str] = []
        for point in points:
            if point not in deduped:
                deduped.append(point)
        base = f"{target_label} 기준으로 오늘 보호자가 확인해야 할 내용은 다음과 같습니다.\n" + "\n".join(
            f"- {point}" for point in deduped[:5]
        )

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_self_check_intent(
    *,
    guide: Guide | None,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    points: list[str] = []

    if schedules:
        schedule_text = _build_schedule_text(schedules, meds)
        for line in schedule_text.splitlines():
            clean = line.strip().lstrip("-").strip()
            if clean:
                points.append(clean)

    if guide and isinstance(guide.content_json, dict):
        for section in guide.content_json.get("sections") or []:
            title = str(section.get("title") or "")
            body = str(section.get("body") or "").strip()
            if "주의" in title or "생활" in title:
                for line in body.splitlines():
                    clean = line.strip().lstrip("-").strip()
                    if clean:
                        points.append(clean)

    deduped: list[str] = []
    for point in points:
        if point not in deduped:
            deduped.append(point)

    if deduped:
        base = f"{target_label} 기준으로 오늘 본인이 확인하면 좋은 체크리스트는 다음과 같습니다.\n" + "\n".join(
            f"- {point}" for point in deduped[:4]
        )
    else:
        base = f"{target_label} 기준으로 오늘 확인할 체크리스트 정보가 아직 충분하지 않습니다."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_allergy_food_intent(
    *,
    profile: PatientProfile | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    allergies = _split_text_items(getattr(profile, "allergies", None) if profile else None)

    if allergies:
        base = f"{target_label} 기준으로 특히 조심해야 할 알레르기/음식 정보는 다음과 같습니다.\n" + "\n".join(
            f"- {item}" for item in allergies
        )
    else:
        base = f"{target_label} 기준으로 등록된 알레르기나 음식 주의 정보는 아직 없습니다."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_missed_dose_intent(
    *,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    base = (
        f"{target_label} 기준으로 복약을 놓쳤을 때는 바로 추가 복용을 단정하기보다, 처방 지시나 약 봉투 안내를 먼저 확인하는 것이 안전합니다.\n"
        "- 다음 복용 시간이 매우 가까우면 임의로 두 번 먹이지 말고\n"
        "- 현재 증상이나 이상 반응이 있으면 의료진이나 약사와 상담해 주세요."
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_emergency_guidance_intent(
    *,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    base = (
        f"{target_label} 기준으로 바로 병원이나 119를 생각해야 하는 신호는 다음과 같습니다.\n"
        "- 숨쉬기 힘들어지거나 호흡이 가빠질 때\n"
        "- 입술이 파래지거나 의식이 처지거나 깨우기 어려울 때\n"
        "- 심한 발진, 얼굴 붓기, 전신 두드러기처럼 급격한 이상 반응이 함께 있을 때\n"
        "- 어지러움이 심해져 걷기 어렵거나 쓰러질 것 같을 때"
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_lifestyle_top_intent(
    *,
    guide: Guide | None,
    profile: PatientProfile | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    points: list[str] = []
    if guide and isinstance(guide.content_json, dict):
        for section in guide.content_json.get("sections") or []:
            title = str(section.get("title") or "")
            body = str(section.get("body") or "").strip()
            if "생활" in title or "주의" in title:
                for line in body.split("\n"):
                    clean = line.strip().replace("- ", "")
                    if clean:
                        points.append(clean)
    if not points and guide and guide.content_text:
        points.extend([line.strip() for line in guide.content_text.split(".") if line.strip()])

    if profile:
        sleep_hours = getattr(profile, "avg_sleep_hours_per_day", None)
        exercise_minutes = getattr(profile, "avg_exercise_minutes_per_day", None)
        allergies = _split_text_items(getattr(profile, "allergies", None))

        if allergies:
            points.insert(0, f"음식/알레르기 주의: {', '.join(allergies)}")
        if sleep_hours is not None:
            points.insert(
                1, f"수면: 하루 평균 {sleep_hours}시간으로 기록되어 있어 수면 리듬을 일정하게 유지하는 것이 좋습니다."
            )
        if exercise_minutes is not None:
            points.insert(
                2,
                f"운동: 하루 평균 {exercise_minutes}분 정도로 기록되어 있어 무리하지 않는 범위에서 꾸준히 유지하는 것이 좋습니다.",
            )

    deduped = _dedupe_lines(points, limit=3)
    base = (
        f"{target_label} 기준으로 생활관리에서 특히 중요한 점 3가지는 다음과 같습니다.\n"
        + "\n".join(f"- {item}" for item in deduped)
        if deduped
        else f"{target_label} 기준 생활관리 요약 정보가 아직 충분하지 않습니다."
    )

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_session_summary_intent(
    *,
    meds: list[dict[str, Any]],
    profile: PatientProfile | None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    med_names = (
        ", ".join([str(med.get("display_name")) for med in meds if med.get("display_name")]) or "복용 약 정보 없음"
    )
    conditions = _split_text_items(getattr(profile, "conditions", None) if profile else None)
    cond_text = ", ".join(conditions) if conditions else "기저질환 정보 확인 필요"
    base = (
        f"{target_label}는 {cond_text}가 있고 현재 {med_names} 중심으로 복약 관리가 필요한 상태로 요약할 수 있습니다."
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_rash_intent(
    *,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    base = (
        f"{target_label} 기준으로 약 복용 후 두드러기나 발진이 생기면 추가 복용 전에 상태를 먼저 확인하는 것이 안전합니다.\n"
        "- 숨쉬기 힘듦, 얼굴 붓기, 전신 두드러기가 함께 있으면 즉시 응급진료가 우선이고\n"
        "- 가벼운 피부 발진이라도 복용 약 이름과 발생 시간을 기록해 의료진과 상담해 주세요."
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


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


async def _answer_medication_caution_intent(
    *,
    message: str,
    guide: Guide | None,
    meds: list[dict[str, Any]],
    profile: PatientProfile | None,
    recent_messages: list[ChatMessage] | None,
    matched_med: dict[str, Any] | None = None,
    external_drug_name: str | None = None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    if external_drug_name or _extract_external_drug_name(message, recent_messages):
        return None

    matched_med = matched_med or _extract_target_med(message=message, meds=meds, recent_messages=recent_messages)
    points: list[str] = []

    if matched_med:
        med_name = str(matched_med.get("display_name") or "해당 약").strip()
        med_notes = str(matched_med.get("notes") or "").strip()
        if med_notes:
            points.append(f"{med_name}: {med_notes}")
        lookup = await _lookup_external_med_info(med_name)
        mfds_item = lookup.get("mfds")
        kids_items = lookup.get("kids") or []
        precautions = _first_clean_line(getattr(mfds_item, "precautions", None)) if mfds_item else ""
        if precautions:
            points.append(f"{med_name} 주의사항: {precautions}")
        if "같이" in message or "상호작용" in message or "조심" in message:
            points.append(
                f"{med_name} 복용 후 두통, 발진, 호흡 불편 같은 이상 반응이 있으면 추가 복용 전에 상태를 확인해 주세요."
            )
        if kids_items:
            kids_summary = _first_clean_line(kids_items[0].get("content"))
            if kids_summary:
                points.append(f"추가 안전 근거: {kids_summary}")

    if profile and getattr(profile, "allergies", None):
        raw_allergies = str(profile.allergies).strip()
        if raw_allergies and ("음식" in message or "알레르기" in message):
            points.append(f"등록된 알레르기 정보: {raw_allergies}")

    caution_body = ""
    if guide and isinstance(guide.content_json, dict):
        sections = guide.content_json.get("sections") or []
        for section in sections:
            title = str(section.get("title") or "")
            body = str(section.get("body") or "")
            if "주의" in title or "주의" in body or "신호" in title:
                caution_body = body
                break

    if caution_body:
        for line in caution_body.split("\n"):
            clean = line.strip().lstrip("-").strip()
            if clean and clean not in points and not any(keyword in clean for keyword in ["운동", "수면", "생활"]):
                points.append(clean)

    if not points:
        return None

    base = f"{target_label} 기준으로 특히 주의해서 볼 점은 다음과 같습니다.\n" + "\n".join(
        f"- {point}" for point in _dedupe_lines(points, limit=4)
    )

    if audience == "senior":
        base += "\n어지러움이 있으면 낙상 위험도 함께 조심해 주세요."

    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


def _answer_general_caution_intent(
    *,
    profile: PatientProfile | None,
    guide: Guide | None,
    meds: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    points: list[str] = []

    if profile:
        allergies = _split_text_items(getattr(profile, "allergies", None))
        conditions = _split_text_items(getattr(profile, "conditions", None))
        if allergies:
            points.append("알레르기: " + ", ".join(allergies))
        if conditions:
            points.append("건강 상태: " + ", ".join(conditions))
        sleep_hours = getattr(profile, "avg_sleep_hours_per_day", None)
        if sleep_hours is not None:
            points.append(
                f"수면은 하루 평균 {sleep_hours}시간으로 기록되어 있어, 수면 리듬을 일정하게 유지하는 것이 좋습니다."
            )
        exercise_minutes = getattr(profile, "avg_exercise_minutes_per_day", None)
        if exercise_minutes is not None:
            points.append(
                f"운동은 하루 평균 {exercise_minutes}분으로 기록되어 있어 무리하지 않는 범위에서 꾸준히 유지하는 것이 좋습니다."
            )

    if guide and isinstance(guide.content_json, dict):
        for section in guide.content_json.get("sections") or []:
            title = str(section.get("title") or "")
            body = str(section.get("body") or "").strip()
            if ("주의" in title or "생활" in title) and body:
                first_line = body.splitlines()[0].strip().lstrip("-").strip()
                if first_line and first_line not in points:
                    points.append(first_line)
            if len(points) >= 3:
                break

    if not points and meds:
        for med in meds[:2]:
            med_name = str(med.get("display_name") or "").strip()
            med_notes = str(med.get("notes") or "").strip()
            if med_name and med_notes:
                points.append(f"{med_name}: {med_notes}")

    if not points and schedules:
        schedule_text = _build_schedule_text(schedules, meds)
        first_line = _first_clean_line(schedule_text)
        if first_line and first_line != "등록된 복약 일정 없음":
            points.append(f"복약 일정: {first_line}")

    if not points:
        return None

    base = f"{target_label} 기준으로 지금 특히 주의해서 볼 점은 다음과 같습니다.\n" + "\n".join(
        f"- {point}" for point in _dedupe_lines(points, limit=3)
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


async def _answer_external_med_intent(
    *,
    message: str,
    meds: list[dict[str, Any]],
    recent_messages: list[ChatMessage] | None,
    profile: PatientProfile | None,
    external_drug_name: str | None = None,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    drug_name = external_drug_name or _extract_external_drug_name(message, recent_messages)
    if not drug_name:
        base = (
            f"{target_label} 기준 현재 기록에 없는 약에 대해선 복용 여부를 바로 단정하기 어렵습니다. "
            "약 이름이나 처방 상황을 조금 더 알려주시면 확인 범위를 안내드릴 수 있습니다."
        )
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    subject_particle = _choose_korean_particle(drug_name, ("이", "가"))
    topic_particle = _choose_korean_particle(drug_name, ("은", "는"))

    in_current_meds = any(_contains_keyword(str(med.get("display_name") or ""), drug_name) for med in meds)
    if in_current_meds:
        base = (
            f"{target_label} 기준 현재 기록상 {drug_name}{subject_particle} 복용 약으로 보입니다. "
            f"약 이름을 다시 포함해 질문해 주시면 복용 시간과 주의사항까지 이어서 안내드릴 수 있습니다."
        )
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    lookup = await _lookup_external_med_info(drug_name)
    mfds_item = lookup.get("mfds")
    kids_items = lookup.get("kids") or []

    profile_points: list[str] = []
    if profile:
        allergies = _split_text_items(getattr(profile, "allergies", None))
        conditions = _split_text_items(getattr(profile, "conditions", None))
        sleep_hours = getattr(profile, "avg_sleep_hours_per_day", None)
        exercise_minutes = getattr(profile, "avg_exercise_minutes_per_day", None)
        if allergies:
            profile_points.append("알레르기: " + ", ".join(allergies[:3]))
        if conditions:
            profile_points.append("건강 상태: " + ", ".join(conditions[:3]))
        if sleep_hours is not None:
            profile_points.append(f"수면: 하루 평균 {sleep_hours}시간")
        if exercise_minutes is not None:
            profile_points.append(f"운동: 하루 평균 {exercise_minutes}분")

    if mfds_item:
        parts = [f"{drug_name}{topic_particle} 현재 복용 중인 약으로 기록되어 있지는 않습니다."]
        item_name = str(getattr(mfds_item, "item_name", "") or drug_name).strip()
        efficacy = _summarize_text(getattr(mfds_item, "efficacy", None), max_sentences=1)
        precautions = _summarize_text(getattr(mfds_item, "precautions", None), max_sentences=2)
        dosage_info = _summarize_text(getattr(mfds_item, "dosage_info", None), max_sentences=1)
        if item_name:
            parts.append(f"- 약 정보: {item_name}")
        if efficacy:
            parts.append(f"- 용도: {efficacy}")
        if precautions:
            parts.append(f"- 특히 조심할 점: {precautions}")
        if dosage_info:
            parts.append(f"- 복용 참고: {dosage_info}")
        if kids_items:
            first_kids = _summarize_text(kids_items[0].get("content"), max_sentences=1)
            if first_kids:
                parts.append(f"- 추가 안전 근거: {first_kids}")
        if profile_points:
            parts.append("- 현재 건강기록 기준 주의점: " + " / ".join(profile_points[:2]))
        parts.append(
            "실제 복용 전에는 처방 여부와 성분을 다시 확인하고, 복용 판단은 의료진이나 약사와 상의하는 것이 좋습니다."
        )
        base = "\n".join(parts)
        return (
            _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base
        )

    base = (
        f"{target_label} 기준 현재 기록된 복용 약 목록에는 {drug_name}{subject_particle} 보이지 않습니다. "
        f"새로 처방받은 약인지, 현재 복용 중인 약인지 먼저 확인하는 것이 좋습니다. "
        + (f"현재 건강기록 기준 주의할 점은 {' / '.join(profile_points[:3])}입니다. " if profile_points else "")
        + f"현재 시스템에서 {drug_name}{topic_particle} 외부 의약 정보 근거로 바로 확인되지는 않았습니다. "
        + "정확한 제품명, 성분명, 처방전 정보가 있으면 더 구체적으로 확인할 수 있습니다."
    )
    return _to_caregiver_style(answer=base, audience=audience) if requester_role == RequesterRole.CAREGIVER else base


# 일상 대화 응답
def _answer_daily_chat(
    *,
    message: str,
    requester_role: RequesterRole,
    target_label: str,
) -> str:
    normalized = (message or "").strip()

    if _contains_any(normalized, ["이름이 뭐", "너 이름", "누구야"]):
        return "저는 복약과 건강 정보를 도와드리는 의료 챗봇입니다."

    if _contains_any(normalized, _BOT_CAPABILITY_KEYWORDS):
        return (
            "저는 복용 중인 약, 복약 시간, 주의사항, 놓친 복약, 알레르기, 생활관리, 보호자 체크포인트를 "
            "기록 기준으로 안내해 드릴 수 있습니다."
        )

    if _contains_any(normalized, ["너 뭐해", "뭘 하는", "뭐 하는 애", "뭐하는 애", "뭐하는 애니"]):
        return "저는 복약 일정, 복용 중인 약, 주의사항, 건강 기록을 기준으로 안내를 도와드리는 의료 챗봇입니다."

    if _contains_any(normalized, ["오늘 어때", "오늘 하루", "기분 어때"]):
        return "저는 괜찮습니다. 오늘도 복약과 건강 관련 질문을 도와드릴 준비가 되어 있습니다."

    if _contains_any(normalized, ["고마워", "감사"]):
        return "도움이 되었다면 다행입니다. 필요한 내용이 있으면 이어서 말씀해 주세요."

    if _contains_any(normalized, ["안녕", "반가워"]):
        return f"안녕하세요. {target_label} 기준으로 복약과 건강 정보를 도와드릴게요."

    if _contains_any(normalized, ["잘 자"]):
        return "편안한 밤 보내세요. 복약 일정이 있다면 잊지 않도록 한 번 더 확인해 주세요."

    return (
        "일상적인 대화도 자연스럽게 도와드릴 수 있습니다. 의료 관련 내용은 기록된 정보 범위 안에서 안내드릴게요."
        if requester_role != RequesterRole.CAREGIVER
        else "일상적인 대화도 가능하지만, 보호자 관점에서는 복약과 상태 확인 중심으로 안내드릴 수 있습니다."
    )


def _extract_core_answer(answer: str, requester_role: RequesterRole) -> str:
    text = str(answer or "").replace(CHAT_DISCLAIMER, "").strip()
    if requester_role != RequesterRole.CAREGIVER:
        return text

    if text.startswith("오늘 확인해보셔야 할 것:") or text.startswith("먼저 확인할 내용:"):
        marker = "오늘 확인해보셔야 할 것:" if text.startswith("오늘 확인해보셔야 할 것:") else "먼저 확인할 내용:"
        body = text.split(marker, 1)[1]
        if "주의 신호:" in body:
            body = body.split("주의 신호:", 1)[0].strip()
        if "위험 신호:" in body:
            body = body.split("위험 신호:", 1)[0].strip()
        if body.startswith("- "):
            body = body[2:]
        return body.strip()

    return text


def _compose_answers(
    *,
    answers: list[str],
    requester_role: RequesterRole,
    audience: str,
) -> str | None:
    parts: list[str] = []
    seen: set[str] = set()
    for answer in answers:
        core = _extract_core_answer(answer, requester_role)
        if core and core not in seen:
            seen.add(core)
            parts.append(core)

    if not parts:
        return None

    combined = "\n\n".join(parts[:3])
    combined = re.sub(r"(회원님 기록 기준으로|선택한 복약자 기준으로)\s*", "", combined)
    combined = combined.strip()
    if requester_role == RequesterRole.CAREGIVER:
        return _to_caregiver_style(answer=combined, audience=audience)
    return combined


def _normalize_intent_order(intents: list[str], requester_role: RequesterRole) -> list[str]:
    ordered: list[str] = []
    skip = set()

    if "external_med" in intents:
        skip.update({"med_detail", "medication_caution", "general_caution", "allergy_food", "guide"})
    if "lifestyle_top" in intents:
        skip.update({"profile_sleep", "profile_exercise", "allergy_food"})
    if "med_time_split" in intents:
        skip.add("med_list")
    if "med_detail" in intents:
        skip.add("schedule")
    if requester_role != RequesterRole.CAREGIVER and "caregiver_check" in intents:
        # 본인 질문에서는 caregiver_check를 self_check로 대체
        intents = [intent for intent in intents if intent != "caregiver_check"] + ["self_check"]

    priority = [
        "rash",
        "missed_dose",
        "emergency_guidance",
        "self_check",
        "caregiver_check",
        "external_med",
        "condition_general",
        "med_detail",
        "medication_caution",
        "general_caution",
        "med_time_split",
        "med_regularity",
        "med_list",
        "schedule",
        "allergy_food",
        "lifestyle_top",
        "session_summary",
        "profile_sleep",
        "profile_exercise",
        "profile_smoking",
        "profile_alcohol",
        "guide",
        "daily",
        "general",
    ]

    for key in priority:
        if key in intents and key not in skip and key not in ordered:
            ordered.append(key)

    for intent in intents:
        if intent not in skip and intent not in ordered:
            ordered.append(intent)

    return ordered


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
    if not content:
        raise RuntimeError("empty llm content")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    return {
        "content": content,
        "is_emergency": False,
        "emergency_message": None,
        "disclaimer": CHAT_DISCLAIMER,
    }


# 일반 fallback 답변
def _fallback_reply(
    *,
    intent: str,
    latest_guide: Guide | None,
    meds: list[dict[str, Any]],
    profile: PatientProfile | None,
    meds_text: str,
    schedule_text: str,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> str:
    summary_points: list[str] = []
    if meds:
        med_names = [
            str(med.get("display_name") or "").strip() for med in meds if str(med.get("display_name") or "").strip()
        ]
        if med_names:
            summary_points.append("현재 기록상 복용 약: " + ", ".join(med_names[:3]))
    if latest_guide and isinstance(latest_guide.content_json, dict):
        for section in latest_guide.content_json.get("sections") or []:
            title = str(section.get("title") or "").strip()
            body = str(section.get("body") or "").strip()
            if title and body:
                summary_points.append(f"{title}: {body.splitlines()[0].strip()}")
            if len(summary_points) >= 3:
                break
    if not summary_points and schedule_text != "등록된 복약 일정 없음":
        first_line = schedule_text.splitlines()[0].strip()
        if first_line:
            summary_points.append(first_line)
    if not summary_points and profile:
        allergies = _split_text_items(getattr(profile, "allergies", None))
        conditions = _split_text_items(getattr(profile, "conditions", None))
        sleep_hours = getattr(profile, "avg_sleep_hours_per_day", None)
        exercise_minutes = getattr(profile, "avg_exercise_minutes_per_day", None)
        if conditions:
            summary_points.append("건강 상태: " + ", ".join(conditions[:3]))
        if allergies:
            summary_points.append("알레르기: " + ", ".join(allergies[:3]))
        if sleep_hours is not None:
            summary_points.append(f"수면: 하루 평균 {sleep_hours}시간")
        if exercise_minutes is not None:
            summary_points.append(f"운동: 하루 평균 {exercise_minutes}분")

    if intent == "general":
        if summary_points:
            base = (
                f"{target_label} 기준으로 지금 바로 연결되는 정보는 다음과 같습니다.\n"
                + "\n".join(f"- {point}" for point in summary_points[:3])
                + "\n궁금한 내용을 약 이름, 증상, 시간대 기준으로 조금 더 구체적으로 말씀해 주세요."
            )
        else:
            base = (
                f"{target_label} 기준으로 바로 답하기에 정보가 충분하지 않습니다. "
                "약 이름, 증상, 복용 시간, 주의사항처럼 질문을 조금 더 구체적으로 말씀해 주세요."
            )
    elif intent == "external_med":
        base = (
            f"{target_label} 기준 현재 기록에 없는 약이라도 일반적인 용도나 주의사항 설명은 가능합니다. "
            "약 이름을 정확히 다시 적어 주시거나 성분명·제품명을 알려주시면, 현재 기록 기준 주의점과 함께 정리해 드릴 수 있습니다."
        )
    elif intent == "condition_general":
        base = (
            f"{target_label} 기준 건강 상태를 보면 "
            + (", ".join(summary_points[:2]) if summary_points else "현재 확인 가능한 건강 정보")
            + "가 보입니다. 특정 질환에 좋은 약은 임의 추천보다 현재 진단과 복용 약을 함께 보고 결정해야 하므로, "
            "원하시면 해당 질환의 일반적인 치료 방향과 현재 기록 기준 주의점을 나눠 설명드릴 수 있습니다."
        )
    else:
        base = (
            f"{target_label} 기준으로 질문과 직접 맞는 답을 확정하긴 어려웠습니다.\n"
            + ("\n".join(f"- {point}" for point in summary_points[:3]) if summary_points else meds_text)
            + "\n약 이름, 증상, 복용 시간 중 하나를 포함해 다시 질문해 주시면 더 정확히 안내드릴 수 있습니다."
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


async def _build_deterministic_answer_parts(
    *,
    analysis: QuestionAnalysis,
    context: PatientChatContext,
    target_label: str,
    requester_role: RequesterRole,
    audience: str,
) -> list[str]:
    deterministic_parts: list[str] = []

    for current_intent in analysis.intents:
        deterministic_answer: str | None = None

        if current_intent in {"profile_smoking", "profile_alcohol", "profile_sleep", "profile_exercise"}:
            deterministic_answer = _answer_profile_intent(
                intent=current_intent,
                profile=context.profile,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "med_time_split":
            deterministic_answer = _answer_med_time_split_intent(
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "med_regularity":
            deterministic_answer = _answer_med_regularity_intent(
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "med_prn":
            deterministic_answer = _answer_med_prn_intent(
                message=analysis.raw_message,
                meds=context.meds,
                schedules=context.schedules,
                recent_messages=context.recent_messages,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "med_detail":
            deterministic_answer = await _answer_med_detail_intent(
                message=analysis.raw_message,
                meds=context.meds,
                schedules=context.schedules,
                recent_messages=context.recent_messages,
                matched_med=analysis.target_med,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "med_list":
            deterministic_answer = _answer_med_list_intent(
                meds=context.meds,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "caregiver_check":
            deterministic_answer = _answer_caregiver_check_intent(
                guide=context.latest_guide,
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "self_check":
            deterministic_answer = _answer_self_check_intent(
                guide=context.latest_guide,
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "allergy_food":
            deterministic_answer = _answer_allergy_food_intent(
                profile=context.profile,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "missed_dose":
            deterministic_answer = _answer_missed_dose_intent(
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "emergency_guidance":
            deterministic_answer = _answer_emergency_guidance_intent(
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "lifestyle_top":
            deterministic_answer = _answer_lifestyle_top_intent(
                guide=context.latest_guide,
                profile=context.profile,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "session_summary":
            deterministic_answer = _answer_session_summary_intent(
                meds=context.meds,
                profile=context.profile,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "rash":
            deterministic_answer = _answer_rash_intent(
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "schedule":
            deterministic_answer = _answer_schedule_intent(
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "medication_caution":
            deterministic_answer = await _answer_medication_caution_intent(
                message=analysis.raw_message,
                guide=context.latest_guide,
                meds=context.meds,
                profile=context.profile,
                recent_messages=context.recent_messages,
                matched_med=analysis.target_med,
                external_drug_name=analysis.external_drug_name,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "general_caution":
            deterministic_answer = _answer_general_caution_intent(
                profile=context.profile,
                guide=context.latest_guide,
                meds=context.meds,
                schedules=context.schedules,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "external_med":
            deterministic_answer = await _answer_external_med_intent(
                message=analysis.raw_message,
                meds=context.meds,
                recent_messages=context.recent_messages,
                profile=context.profile,
                external_drug_name=analysis.external_drug_name,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "guide":
            deterministic_answer = _answer_guide_intent(
                guide=context.latest_guide,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )
        elif current_intent == "daily":
            deterministic_answer = _answer_daily_chat(
                message=analysis.raw_message,
                requester_role=requester_role,
                target_label=target_label,
            )

        if deterministic_answer:
            deterministic_parts.append(deterministic_answer)

    return deterministic_parts


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
        analysis = _analyze_question(
            message=stripped,
            meds=context.meds,
            recent_messages=context.recent_messages,
            requester_role=requester_role,
        )
        is_emergency = analysis.is_emergency
        emergency_message = analysis.emergency_message
        intent = analysis.primary_intent
        llm_preferred = _should_prefer_llm(analysis=analysis)

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
            deterministic_parts = await _build_deterministic_answer_parts(
                analysis=analysis,
                context=context,
                target_label=target_label,
                requester_role=requester_role,
                audience=audience,
            )

            composed_answer = _compose_answers(
                answers=deterministic_parts,
                requester_role=requester_role,
                audience=audience,
            )

            meds_text = _build_meds_text(context.meds)
            schedule_text = _build_schedule_text(context.schedules, context.meds)
            profile_text = _build_profile_text(context.profile)
            guide_text = _build_guide_text(context.latest_guide)
            history_text = _build_history_text(context.recent_messages)
            kids_text = _build_kids_text(context.kids_evidence)
            rag_text = _build_rag_text(context.rag_context)
            deterministic_text = composed_answer or (
                "\n".join(f"- {_extract_core_answer(answer, requester_role)}" for answer in deterministic_parts)
                if deterministic_parts
                else "결정적 사실 요약 없음"
            )
            external_lookup = (
                await _lookup_external_med_info(analysis.external_drug_name) if analysis.external_drug_name else None
            )
            external_drug_text = _build_external_drug_text(
                drug_name=analysis.external_drug_name,
                lookup=external_lookup,
            )

            if llm_preferred:
                try:
                    system_prompt = _read_prompt_template("chat_system_prompt.txt").format(
                        requester_role=requester_role.value,
                        target_label=target_label,
                        answer_mode=analysis.answer_mode,
                        audience_label=_audience_label(audience),
                        extra_safety=_extra_safety_text(audience),
                        kids_text=kids_text,
                        rag_text=rag_text,
                        external_drug_text=external_drug_text,
                        deterministic_text=deterministic_text,
                        disclaimer=CHAT_DISCLAIMER,
                    )
                    user_prompt = _read_prompt_template("chat_user_prompt.txt").format(
                        guide_text=guide_text,
                        meds_text=meds_text,
                        schedule_text=schedule_text,
                        profile_text=profile_text,
                        external_drug_text=external_drug_text,
                        deterministic_text=deterministic_text,
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
                    assistant_content = composed_answer or _fallback_reply(
                        intent=intent,
                        latest_guide=context.latest_guide,
                        meds=context.meds,
                        profile=context.profile,
                        meds_text=meds_text,
                        schedule_text=schedule_text,
                        target_label=target_label,
                        requester_role=requester_role,
                        audience=audience,
                    )
            elif composed_answer:
                assistant_content = composed_answer
            else:
                try:
                    system_prompt = _read_prompt_template("chat_system_prompt.txt").format(
                        requester_role=requester_role.value,
                        target_label=target_label,
                        answer_mode=analysis.answer_mode,
                        audience_label=_audience_label(audience),
                        extra_safety=_extra_safety_text(audience),
                        kids_text=kids_text,
                        rag_text=rag_text,
                        external_drug_text=external_drug_text,
                        deterministic_text=deterministic_text,
                        disclaimer=CHAT_DISCLAIMER,
                    )
                    user_prompt = _read_prompt_template("chat_user_prompt.txt").format(
                        guide_text=guide_text,
                        meds_text=meds_text,
                        schedule_text=schedule_text,
                        profile_text=profile_text,
                        external_drug_text=external_drug_text,
                        deterministic_text=deterministic_text,
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
                        intent=intent,
                        latest_guide=context.latest_guide,
                        meds=context.meds,
                        profile=context.profile,
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
