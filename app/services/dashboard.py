from datetime import date, timedelta

from tortoise.expressions import Q
from tortoise.functions import Count

from app.dtos.dashboard import ChartDataPoint, DashboardResponse, DashboardStatsResponse, OCRAnalysis
from app.models.documents import Document, OcrJob
from app.models.guides import Guide
from app.models.users import User


class DashboardService:
    @staticmethod
    async def get_dashboard_data(period_days: int = 7) -> DashboardResponse:
        today = date.today()
        yesterday = today - timedelta(days=1)
        period_start = today - timedelta(days=period_days)

        # 통계 계산
        total_users = await User.all().count()
        yesterday_users = await User.filter(created_at__lt=today).count()
        users_change = ((total_users - yesterday_users) / yesterday_users * 100) if yesterday_users > 0 else 0

        today_guides = await Guide.filter(created_at__date=today).count()
        yesterday_guides = await Guide.filter(created_at__date=yesterday).count()
        guides_change = (
            ((today_guides - yesterday_guides) / yesterday_guides * 100) if yesterday_guides > 0 else 0
        )

        # OCR 성공률 (OcrJob 모델 기준)
        today_ocr = await OcrJob.filter(created_at__date=today).count()
        today_success_ocr = await OcrJob.filter(created_at__date=today, status="completed").count()
        ocr_success_rate = (today_success_ocr / today_ocr * 100) if today_ocr > 0 else 0

        yesterday_ocr = await OcrJob.filter(created_at__date=yesterday).count()
        yesterday_success_ocr = await OcrJob.filter(created_at__date=yesterday, status="completed").count()
        yesterday_ocr_rate = (yesterday_success_ocr / yesterday_ocr * 100) if yesterday_ocr > 0 else 0
        ocr_change = ocr_success_rate - yesterday_ocr_rate

        # 챗봇 요청 (가정: Chat 모델 사용)
        today_chatbot = 0
        yesterday_chatbot = 0
        chatbot_change = 0

        # 시스템 에러 (가정: 에러 로그 모델)
        system_errors = 8
        system_errors_change = -33.3

        stats = DashboardStatsResponse(
            total_users=total_users,
            today_guides=today_guides,
            ocr_success_rate=round(ocr_success_rate, 1),
            today_chatbot_requests=today_chatbot,
            system_errors=system_errors,
            total_users_change=round(users_change, 1),
            today_guides_change=round(guides_change, 1),
            ocr_success_rate_change=round(ocr_change, 1),
            today_chatbot_requests_change=round(chatbot_change, 1),
            system_errors_change=system_errors_change,
        )

        # 가이드 생성 추이
        guide_trend = []
        for i in range(period_days):
            target_date = period_start + timedelta(days=i)
            count = await Guide.filter(created_at__date=target_date).count()
            guide_trend.append(ChartDataPoint(date=target_date, value=count))

        # 챗봇 요청 추이
        chatbot_trend = []
        for i in range(period_days):
            target_date = period_start + timedelta(days=i)
            count = 0
            chatbot_trend.append(ChartDataPoint(date=target_date, value=count))

        # OCR 분석
        total_processed = await OcrJob.all().count()
        success_count = await OcrJob.filter(status="completed").count()
        failure_count = await OcrJob.filter(status="failed").count()
        success_rate = (success_count / total_processed * 100) if total_processed > 0 else 0

        # 실패 사유 Top 3 (가정)
        top_failures = [
            ("이미지 해상도 부족", 142),
            ("텍스트 인식 실패", 89),
            ("이미지 형식 미지원", 58),
        ]

        ocr_analysis = OCRAnalysis(
            total_processed=total_processed,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_rate, 1),
            top_failures=top_failures,
        )

        return DashboardResponse(
            stats=stats, guide_trend=guide_trend, chatbot_trend=chatbot_trend, ocr_analysis=ocr_analysis
        )
