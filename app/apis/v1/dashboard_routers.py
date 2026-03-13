from fastapi import APIRouter, Depends, Query

from app.dependencies.security import get_request_user
from app.dtos.dashboard import DashboardResponse
from app.models.users import User
from app.services.dashboard import DashboardService

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get("", response_model=DashboardResponse)
async def get_dashboard(
    period: int = Query(7, ge=1, le=30, description="조회 기간 (일)"),
    current_user: User = Depends(get_request_user),
) -> DashboardResponse:
    """관리자 대시보드 데이터 조회 (임시로 모든 사용자 허용)"""
    # 임시로 모든 로그인 사용자에게 허용 (role 컴럼이 없어서)
    # 추후 role 컴럼 추가 후 제한 가능
    
    return await DashboardService.get_dashboard_data(period_days=period)
