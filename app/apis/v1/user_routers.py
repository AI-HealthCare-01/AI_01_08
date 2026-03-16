from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, UserUpdateRequest
from app.models.patients import Patient
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    patient = await Patient.get_or_none(user_id=user.id)

    response_data = UserInfoResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone_number=user.phone_number,
        birthday=user.birthday,
        gender=user.gender,
        created_at=user.created_at,
        patient_id=patient.id if patient else None,
    )

    return Response(response_data.model_dump(), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    patient = await Patient.get_or_none(user_id=updated_user.id)

    response_data = UserInfoResponse(
        id=updated_user.id,
        name=updated_user.name,
        email=updated_user.email,
        phone_number=updated_user.phone_number,
        birthday=updated_user.birthday,
        gender=updated_user.gender,
        created_at=updated_user.created_at,
        patient_id=patient.id if patient else None,
    )

    return Response(response_data.model_dump(), status_code=status.HTTP_200_OK)