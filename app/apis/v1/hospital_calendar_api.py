# app/apis/v1/hospital_calendar_api.py

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from app.dtos.hospital_calendar_dtos import (
    HospitalScheduleCreateRequest,
    HospitalScheduleListResponse,
    HospitalScheduleResponse,
    HospitalScheduleUpdateRequest,
)
from app.services.hospital_calendar_service import HospitalCalendarService

router = APIRouter(
    prefix="/calendar/hospital",
    tags=["hospital-calendar"],
)


@router.post(
    "",
    response_model=HospitalScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital_schedule(
    request: HospitalScheduleCreateRequest,
) -> HospitalScheduleResponse:
    """
    병원 일정 생성

    실제 최종 경로:
    POST /api/v1/calendar/hospital
    """
    service = HospitalCalendarService()

    # 현재 인증 연동 전이므로 created_by_user_id 는 None 처리
    # 나중에 인증 붙으면 get_request_user 등으로 current_user.id 넣으면 됨
    return await service.create_schedule(
        request=request,
        created_by_user_id=None,
    )


@router.get(
    "",
    response_model=HospitalScheduleListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_hospital_schedules(
    patient_id: int | None = Query(
        default=None,
        description="환자 ID 기준 병원 일정 조회",
    ),
) -> HospitalScheduleListResponse:
    """
    병원 일정 목록 조회

    실제 최종 경로:
    GET /api/v1/calendar/hospital
    """
    service = HospitalCalendarService()
    items = await service.get_schedules(patient_id=patient_id)
    return HospitalScheduleListResponse(items=items)


@router.patch(
    "/{id}",
    response_model=HospitalScheduleResponse,
    status_code=status.HTTP_200_OK,
)
async def update_hospital_schedule(
    id: int,
    request: HospitalScheduleUpdateRequest,
) -> HospitalScheduleResponse:
    """
    병원 일정 수정

    실제 최종 경로:
    PATCH /api/v1/calendar/hospital/{id}
    """
    service = HospitalCalendarService()
    return await service.update_schedule(schedule_id=id, request=request)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_hospital_schedule(id: int) -> Response:
    """
    병원 일정 삭제

    실제 최종 경로:
    DELETE /api/v1/calendar/hospital/{id}
    """
    service = HospitalCalendarService()
    await service.delete_schedule(schedule_id=id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
