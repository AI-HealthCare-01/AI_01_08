from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from starlette import status

from app.models.healthcare import UserRole
from app.models.patients import CaregiverPatientLink, Patient
from app.models.users import User

ActorType = Literal["PATIENT", "CAREGIVER", "ADMIN"]


# ------------------------------------------------------------
# 현재 사용자의 역할을 판정하는 함수
# ------------------------------------------------------------
async def resolve_actor_role(user: User) -> ActorType:
    if await UserRole.filter(user_id=user.id, role__name="ADMIN").exists():
        return "ADMIN"
    if await UserRole.filter(user_id=user.id, role__name="CAREGIVER").exists():
        return "CAREGIVER"
    return "PATIENT"


# ------------------------------------------------------------
# 환자 역할 여부를 검증하는 함수
# ------------------------------------------------------------
async def require_patient_role(user: User) -> None:
    if await UserRole.filter(user_id=user.id, role__name="PATIENT").exists():
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="환자 전용 기능입니다. 계정 역할을 다시 확인해 주세요.",
    )


# ------------------------------------------------------------
# 보호자 역할 여부를 검증하는 함수
# ------------------------------------------------------------
async def require_caregiver_role(user: User) -> None:
    if await UserRole.filter(user_id=user.id, role__name="CAREGIVER").exists():
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="보호자 전용 기능입니다. 계정 역할을 다시 확인해 주세요.",
    )


# ------------------------------------------------------------
# 내 계정에 연결된 Patient row 를 찾는 함수
# ------------------------------------------------------------
async def get_my_patient_or_404(user: User) -> Patient:
    await require_patient_role(user)

    patient = await Patient.get_or_none(user_id=user.id)
    if not patient:
        patient = await Patient.get_or_none(owner_user_id=user.id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="본인에게 연결된 복약자 정보를 찾을 수 없습니다.",
        )

    return patient


# ------------------------------------------------------------
# 보호자의 link_id 로 연동된 Patient row 를 찾는 함수
# ------------------------------------------------------------
async def get_linked_patient_or_404(caregiver: User, link_id: int) -> Patient:
    await require_caregiver_role(caregiver)

    link = await CaregiverPatientLink.get_or_none(
        id=link_id,
        caregiver_user_id=caregiver.id,
        status="active",
        revoked_at__isnull=True,
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 복약자에 대한 접근 권한이 없습니다. 연동 상태를 확인해 주세요.",
        )

    patient = await Patient.get_or_none(id=link.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="연결된 복약자 정보를 찾을 수 없습니다.",
        )

    return patient


# ------------------------------------------------------------
# 기존 구조 호환용: patient_id 직접 접근 권한을 판정하는 함수
# ------------------------------------------------------------
async def assert_can_access_patient(user: User, patient_id: int, action: str) -> ActorType:
    if await UserRole.filter(user_id=user.id, role__name="ADMIN").exists():
        return "ADMIN"

    patient = await Patient.get_or_none(id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상 복약자 정보를 찾을 수 없습니다.",
        )

    if patient.user_id == user.id or patient.owner_user_id == user.id:
        return "PATIENT"

    linked = await CaregiverPatientLink.filter(
        caregiver_user_id=user.id,
        patient_id=patient_id,
        status="active",
        revoked_at__isnull=True,
    ).exists()

    if linked:
        return "CAREGIVER"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="해당 복약자에 대한 접근 권한이 없습니다. 연동 상태를 확인해 주세요.",
    )
