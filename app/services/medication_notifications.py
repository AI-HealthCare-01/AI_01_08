from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from tortoise.expressions import Q

from app.models.notification_settings import NotificationSettings
from app.models.notifications import Notification
from app.models.schedules import IntakeLog, MedSchedule, MedScheduleTime
from app.services.medication_intake_service import (
    GRACE_MINUTES,
    _normalize_time_of_day,
    _parse_days_of_week,
)
from app.services.queue_service import enqueue_send_notification

INTAKE_REMINDER_TYPE = "intake_reminder"
MISSED_ALERT_TYPE = "missed_alert"


@dataclass(slots=True)
class MedicationSlot:
    patient_id: int
    patient_user_id: int | None
    patient_name: str | None
    schedule_id: int
    schedule_time_id: int
    patient_med_id: int
    medication_name: str | None
    scheduled_at: datetime
    caregiver_user_ids: list[int]


def _daterange(date_from: date, date_to: date) -> list[date]:
    days: list[date] = []
    current = date_from
    while current <= date_to:
        days.append(current)
        current += timedelta(days=1)
    return days


def _build_reminder_key(slot: MedicationSlot, stage: str) -> str:
    return f"med:{slot.patient_id}:{slot.schedule_id}:{slot.schedule_time_id}:{slot.scheduled_at.isoformat()}:{stage}"


def _build_slot_payload(slot: MedicationSlot, stage: str) -> dict[str, object]:
    return {
        "patient_id": slot.patient_id,
        "patient_name": slot.patient_name,
        "schedule_id": slot.schedule_id,
        "schedule_time_id": slot.schedule_time_id,
        "patient_med_id": slot.patient_med_id,
        "medication_name": slot.medication_name,
        "scheduled_at": slot.scheduled_at.isoformat(),
        "scheduled_date": slot.scheduled_at.date().isoformat(),
        "type_stage": stage,
        "reminder_key": _build_reminder_key(slot, stage),
    }


def _build_intake_message(slot: MedicationSlot) -> tuple[str, str]:
    medication_name = slot.medication_name or "복약"
    scheduled_label = slot.scheduled_at.strftime("%H:%M")
    return "복약 시간이에요", f"{medication_name} 복용 시간({scheduled_label})이에요. 복용 여부를 확인해 주세요."


def _build_missed_message(slot: MedicationSlot) -> tuple[str, str]:
    patient_name = slot.patient_name or "환자"
    medication_name = slot.medication_name or "약"
    scheduled_label = slot.scheduled_at.strftime("%H:%M")
    return (
        "복약 확인이 필요해요",
        f"{patient_name}님의 {medication_name} 복용 기록이 {scheduled_label} 이후 아직 없어요. 확인해 주세요.",
    )


async def _is_notification_enabled(user_id: int, field_name: str) -> bool:
    settings = await NotificationSettings.get_or_none(user_id=user_id)
    if settings is None:
        return True
    return bool(getattr(settings, field_name, True))


async def _notification_already_created(user_id: int, notification_type: str, reminder_key: str) -> bool:
    return await Notification.filter(
        user_id=user_id,
        type=notification_type,
        payload_json__contains=f'"reminder_key":"{reminder_key}"',
    ).exists()


async def _load_candidate_slots(window_start: datetime, window_end: datetime) -> list[MedicationSlot]:  # noqa: C901
    grace = timedelta(minutes=GRACE_MINUTES)
    range_start = (window_start - grace).date()
    range_end = window_end.date()

    schedules = await MedSchedule.filter(
        Q(status="active"),
        Q(start_date__isnull=True) | Q(start_date__lte=range_end),
        Q(end_date__isnull=True) | Q(end_date__gte=range_start),
    ).prefetch_related("patient", "patient__caregiver_links", "patient_med")
    if not schedules:
        return []

    schedule_ids = [schedule.id for schedule in schedules]
    schedule_times = await MedScheduleTime.filter(schedule_id__in=schedule_ids, is_active=True).all()
    times_by_schedule: dict[int, list[MedScheduleTime]] = {}
    for schedule_time in schedule_times:
        times_by_schedule.setdefault(schedule_time.schedule_id, []).append(schedule_time)

    log_start = datetime.combine(range_start, time.min)
    log_end = datetime.combine(range_end + timedelta(days=1), time.min)
    logs = await IntakeLog.filter(scheduled_at__gte=log_start, scheduled_at__lt=log_end).all()
    log_map: dict[tuple[int, datetime], IntakeLog] = {}
    for log in logs:
        key = (log.schedule_time_id, log.scheduled_at.replace(microsecond=0))
        log_map[key] = log

    slots: list[MedicationSlot] = []
    for schedule in schedules:
        caregiver_user_ids = [
            int(link.caregiver_user_id)
            for link in getattr(schedule.patient, "caregiver_links", [])
            if getattr(link, "status", None) == "active" and getattr(link, "revoked_at", None) is None
        ]
        patient_name = getattr(schedule.patient, "display_name", None)
        medication_name = getattr(getattr(schedule, "patient_med", None), "display_name", None)

        for day in _daterange(range_start, range_end):
            if schedule.start_date and day < schedule.start_date:
                continue
            if schedule.end_date and day > schedule.end_date:
                continue

            for schedule_time in times_by_schedule.get(schedule.id, []):
                allowed_days = _parse_days_of_week(schedule_time.days_of_week)
                if allowed_days is not None and day.weekday() not in allowed_days:
                    continue

                slot_time = _normalize_time_of_day(schedule_time.time_of_day)
                scheduled_at = datetime.combine(day, slot_time).replace(microsecond=0)
                key = (schedule_time.id, scheduled_at)

                # Any existing log means the slot is already handled.
                if key in log_map:
                    continue

                slots.append(
                    MedicationSlot(
                        patient_id=schedule.patient_id,
                        patient_user_id=getattr(schedule.patient, "user_id", None),
                        patient_name=patient_name,
                        schedule_id=schedule.id,
                        schedule_time_id=schedule_time.id,
                        patient_med_id=schedule.patient_med_id,
                        medication_name=medication_name,
                        scheduled_at=scheduled_at,
                        caregiver_user_ids=caregiver_user_ids,
                    )
                )

    return slots


async def dispatch_due_medication_notifications(*, window_start: datetime, window_end: datetime) -> int:
    grace = timedelta(minutes=GRACE_MINUTES)
    created_count = 0
    slots = await _load_candidate_slots(window_start, window_end)

    for slot in slots:
        intake_due = window_start <= slot.scheduled_at < window_end
        missed_due = window_start <= (slot.scheduled_at + grace) < window_end

        if intake_due and slot.patient_user_id:
            reminder_key = _build_reminder_key(slot, "intake")
            if await _is_notification_enabled(
                slot.patient_user_id, "intake_reminder"
            ) and not await _notification_already_created(
                slot.patient_user_id,
                INTAKE_REMINDER_TYPE,
                reminder_key,
            ):
                title, body = _build_intake_message(slot)
                payload_json = json.dumps(
                    _build_slot_payload(slot, "intake"), ensure_ascii=False, separators=(",", ":")
                )
                notif = await Notification.create(
                    user_id=slot.patient_user_id,
                    patient_id=slot.patient_id,
                    type=INTAKE_REMINDER_TYPE,
                    title=title,
                    body=body,
                    payload_json=payload_json,
                    sent_at=None,
                )
                await enqueue_send_notification(notif.id)
                created_count += 1

        if missed_due and slot.caregiver_user_ids:
            reminder_key = _build_reminder_key(slot, "missed")
            title, body = _build_missed_message(slot)
            payload_json = json.dumps(_build_slot_payload(slot, "missed"), ensure_ascii=False, separators=(",", ":"))

            for caregiver_user_id in slot.caregiver_user_ids:
                if not await _is_notification_enabled(caregiver_user_id, "missed_alert"):
                    continue
                if await _notification_already_created(caregiver_user_id, MISSED_ALERT_TYPE, reminder_key):
                    continue

                notif = await Notification.create(
                    user_id=caregiver_user_id,
                    patient_id=slot.patient_id,
                    type=MISSED_ALERT_TYPE,
                    title=title,
                    body=body,
                    payload_json=payload_json,
                    sent_at=None,
                )
                await enqueue_send_notification(notif.id)
                created_count += 1

    return created_count
