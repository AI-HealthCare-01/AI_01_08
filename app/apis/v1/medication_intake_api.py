# app/apis/v1/medication_intake_api.py
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.dtos.medication_intake_dtos import IntakeStatusResponse
from app.services.medication_intake_service import MedicationIntakeService

router = APIRouter(prefix="/v1/medication", tags=["Medication"])


def get_service() -> MedicationIntakeService:
    return MedicationIntakeService()


@router.get("/patients/{patient_id}/intake-status", response_model=IntakeStatusResponse)
async def get_patient_intake_status(
    patient_id: int,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    svc: MedicationIntakeService = Depends(get_service),
) -> IntakeStatusResponse:
    """
    환자 복약 현황 조회 (REQ-EXT-004)
    - 기간(from~to) 동안의 복약 상태(taken/missed/pending/skipped) 및 이행률 요약을 반환
    """
    return await svc.get_patient_intake_status(patient_id, date_from, date_to)