# app/services/medication_intake_service.py
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from app.dtos.medication_intake_dtos import (
    AdherenceSummary,
    DailyIntakeStatus,
    IntakeItem,
    IntakeStatusResponse,
)
from app.repositories.intake_log_repository import IntakeLogRepository
from app.repositories.med_schedule_repository import MedScheduleRepository

GRACE_MINUTES = 60


def _parse_days_of_week(days_str: Optional[str]) -> Optional[set[int]]:
    """
    days_of_week 예: '1,2,3,4,5,6,7'
    규칙: 1=일요일, 7=토요일
    None이면 매일로 처리
    """
    if not days_str:
        return None
    return {int(x.strip()) for x in days_str.split(",") if x.strip()}


def _dow_sun1(d: date) -> int:
    """
    Python weekday(): 월0~일6
    우리 규칙: 일1~토7
    """
    return ((d.weekday() + 1) % 7) + 1


def _daterange(date_from: date, date_to: date) -> List[date]:
    days = []
    cur = date_from
    while cur <= date_to:
        days.append(cur)
        cur += timedelta(days=1)
    return days


class MedicationIntakeService:
    def __init__(self) -> None:
        self.intake_repo = IntakeLogRepository()
        self.schedule_repo = MedScheduleRepository()

    async def get_patient_intake_status(
        self,
        patient_id: int,
        date_from: date,
        date_to: date,
        now: Optional[datetime] = None,
    ) -> IntakeStatusResponse:
        if now is None:
            now = datetime.now()

        schedules = await self.schedule_repo.list_active_schedules_by_patient_in_range(
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        schedule_ids = [s.id for s in schedules]

        schedule_times = await self.schedule_repo.list_times_by_schedule_ids(schedule_ids)

        times_by_schedule: Dict[int, List] = {}
        for t in schedule_times:
            times_by_schedule.setdefault(t.schedule_id, []).append(t)

        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min)

        logs = await self.intake_repo.list_logs_by_patient_and_range(
            patient_id=patient_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        log_map: Dict[Tuple[int, datetime], object] = {}
        for log in logs:
            log_map[(log.schedule_time_id, log.scheduled_at)] = log

        grace = timedelta(minutes=GRACE_MINUTES)

        daily_list: List[DailyIntakeStatus] = []
        expected_total = 0
        taken = 0
        missed = 0
        pending = 0
        skipped = 0

        for day in _daterange(date_from, date_to):
            items: List[IntakeItem] = []

            for schedule in schedules:
                if day < schedule.start_date or day > schedule.end_date:
                    continue

                for schedule_time in times_by_schedule.get(schedule.id, []):
                    allowed_days = _parse_days_of_week(schedule_time.days_of_week)
                    if allowed_days is not None and _dow_sun1(day) not in allowed_days:
                        continue

                    scheduled_at = datetime.combine(day, schedule_time.time_of_day)
                    expected_total += 1

                    log = log_map.get((schedule_time.id, scheduled_at))

                    if log:
                        status_value = log.status

                        if status_value == "taken":
                            taken += 1
                        elif status_value == "missed":
                            missed += 1
                        elif status_value == "skipped":
                            skipped += 1
                        else:
                            status_value = "pending"
                            pending += 1

                        items.append(
                            IntakeItem(
                                schedule_id=schedule.id,
                                schedule_time_id=schedule_time.id,
                                patient_med_id=schedule.patient_med_id,
                                scheduled_at=scheduled_at,
                                status=status_value,
                                taken_at=log.taken_at,
                                note=log.note,
                            )
                        )
                    else:
                        if now >= scheduled_at + grace:
                            status_value = "missed"
                            missed += 1
                        else:
                            status_value = "pending"
                            pending += 1

                        items.append(
                            IntakeItem(
                                schedule_id=schedule.id,
                                schedule_time_id=schedule_time.id,
                                patient_med_id=schedule.patient_med_id,
                                scheduled_at=scheduled_at,
                                status=status_value,
                                taken_at=None,
                                note=None,
                            )
                        )

            items.sort(key=lambda x: x.scheduled_at)
            daily_list.append(DailyIntakeStatus(day=day, items=items))

        overall_rate = (taken / expected_total) if expected_total else 0.0
        completed_denominator = taken + missed + skipped
        completed_rate = (
            (taken / completed_denominator) if completed_denominator else None
        )

        summary = AdherenceSummary(
            expected_total=expected_total,
            taken=taken,
            missed=missed,
            pending=pending,
            skipped=skipped,
            overall_rate=round(overall_rate, 4),
            completed_rate=round(completed_rate, 4) if completed_rate is not None else None,
        )

        return IntakeStatusResponse(
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            days=daily_list,
            summary=summary,
        )