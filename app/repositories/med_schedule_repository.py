# app/repositories/med_schedule_repository.py
from __future__ import annotations

from datetime import date
from typing import List, Optional

from app.models.schedules import MedSchedule, MedScheduleTime


class MedScheduleRepository:
    async def list_active_schedules_by_patient_in_range(
        self,
        patient_id: int,
        date_from: date,
        date_to: date,
    ) -> List[MedSchedule]:
        """
        특정 환자의 기간과 겹치는 active 복약 스케줄 조회
        - [date_from, date_to]와 스케줄 기간이 겹치는 것만 조회
        """
        return await MedSchedule.filter(
            patient_id=patient_id,
            status="active",
            start_date__lte=date_to,
            end_date__gte=date_from,
        ).all()

    async def list_times_by_schedule_ids(
        self,
        schedule_ids: List[int],
    ) -> List[MedScheduleTime]:
        """
        스케줄 ID 목록에 해당하는 활성 복용 시간 조회
        """
        if not schedule_ids:
            return []

        return await MedScheduleTime.filter(
            schedule_id__in=schedule_ids,
            is_active=True,
        ).all()

    async def get_schedule_by_id(
        self,
        schedule_id: int,
    ) -> Optional[MedSchedule]:
        """
        단건 스케줄 조회
        """
        return await MedSchedule.get_or_none(id=schedule_id)

    async def get_schedule_time_by_id(
        self,
        schedule_time_id: int,
    ) -> Optional[MedScheduleTime]:
        """
        단건 스케줄 시간 조회
        """
        return await MedScheduleTime.get_or_none(id=schedule_time_id)

    async def get_active_schedule_time_by_id(
        self,
        schedule_time_id: int,
    ) -> Optional[MedScheduleTime]:
        """
        활성 상태의 스케줄 시간만 조회
        """
        return await MedScheduleTime.get_or_none(
            id=schedule_time_id,
            is_active=True,
        )