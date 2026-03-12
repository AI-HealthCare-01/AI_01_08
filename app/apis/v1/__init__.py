from fastapi import APIRouter, Depends

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.invitation_routers import invitation_router
from app.apis.v1.notification_routers import notification_router
from app.apis.v1.public_routers import public_router
from app.apis.v1.user_routers import user_router
from app.dependencies.security import get_request_user

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(public_router)
v1_routers.include_router(user_router, dependencies=[Depends(get_request_user)])
v1_routers.include_router(invitation_router, dependencies=[Depends(get_request_user)])

# 20260303 알림설정 HYJ
v1_routers.include_router(notification_router, dependencies=[Depends(get_request_user)])
