# app/repositories/intake_log_repository.py
from __future__ import annotations

from datetime import datetime
from typing import List

from app.models.schedules import IntakeLog


class IntakeLogRepository:

    async def list_logs_by_patient_and_range(
        self,
        patient_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> List[IntakeLog]:
        """
        특정 환자의 기간 내 복약 로그 조회
        """
        return await IntakeLog.filter(
            patient_id=patient_id,
            scheduled_at__gte=start_dt,
            scheduled_at__lt=end_dt,
        ).all()