#!/usr/bin/env python3
"""
대시보드 테스트용 샘플 데이터 생성 스크립트
"""

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def create_sample_data():
    """샘플 데이터 생성"""
    from tortoise import Tortoise

    from app.core.config import get_settings
    from app.models.documents import OcrJob
    from app.models.guides import Guide
    from app.models.patients import Patient
    from app.models.users import Gender, User

    settings = get_settings()

    # 데이터베이스 연결
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["app.models"]},
    )

    print("🔄 샘플 데이터 생성 중...")

    # 1. 사용자 데이터 생성
    users_created = await _create_users(User, Gender)

    print(f"✅ 사용자 {users_created}명 생성 완료")

    # 2. 환자 데이터 생성
    patients_created = await _create_patients(Patient, Gender)

    print(f"✅ 환자 {patients_created}명 생성 완료")

    # 3. 가이드 데이터 생성 (최근 30일간)
    patients = await Patient.all()
    guides_created = await _create_guides(Guide, patients)

    print(f"✅ 가이드 {guides_created}개 생성 완료")

    # 4. OCR Job 데이터 생성
    ocr_jobs_created = await _create_ocr_jobs(OcrJob)

    print(f"✅ OCR Job {ocr_jobs_created}개 생성 완료")

    # 데이터베이스 연결 종료
    await Tortoise.close_connections()

    print("🎉 샘플 데이터 생성 완료!")
    print(f"   - 사용자: {users_created}명")
    print(f"   - 환자: {patients_created}명")
    print(f"   - 가이드: {guides_created}개")
    print(f"   - OCR Job: {ocr_jobs_created}개")


async def _create_users(user_model, gender_model) -> int:
    users_created = 0
    for i in range(10):
        try:
            await user_model.create(
                email=f"test_user_{i}@example.com",
                name=f"테스트사용자{i}",
                gender=gender_model.MALE if i % 2 == 0 else gender_model.FEMALE,
                birthday=date(1990, 1, 1) + timedelta(days=i * 30),
                phone_number=f"010-0000-{1000 + i}",
                nickname=f"닉네임{i}",
                is_active=True,
                created_at=datetime.now() - timedelta(days=i),
            )
            users_created += 1
        except Exception as e:
            print(f"사용자 {i} 생성 실패: {e}")
    return users_created


async def _create_patients(patient_model, gender_model) -> int:
    patients_created = 0
    for i in range(5):
        try:
            await patient_model.create(
                name=f"환자{i}",
                gender=gender_model.MALE if i % 2 == 0 else gender_model.FEMALE,
                birthday=date(1980, 1, 1) + timedelta(days=i * 60),
                phone_number=f"010-1111-{2000 + i}",
                created_at=datetime.now() - timedelta(days=i * 2),
            )
            patients_created += 1
        except Exception as e:
            print(f"환자 {i} 생성 실패: {e}")
    return patients_created


async def _create_guides(guide_model, patients) -> int:
    guides_created = 0
    for i in range(50):
        try:
            patient = patients[i % len(patients)] if patients else None
            if patient:
                await guide_model.create(
                    patient=patient,
                    status="completed" if i % 3 != 0 else "processing",
                    content=f"가이드 내용 {i}",
                    created_at=datetime.now() - timedelta(days=i // 2, hours=i % 24),
                )
                guides_created += 1
        except Exception as e:
            print(f"가이드 {i} 생성 실패: {e}")
    return guides_created


async def _create_ocr_jobs(ocr_job_model) -> int:
    ocr_jobs_created = 0
    for i in range(100):
        try:
            status = "completed" if i % 4 != 0 else ("failed" if i % 8 == 0 else "processing")
            error_message = None

            if status == "failed":
                error_messages = [
                    "이미지 해상도가 너무 낮습니다",
                    "텍스트를 인식할 수 없습니다",
                    "지원하지 않는 이미지 형식입니다",
                    "파일이 손상되었습니다",
                ]
                error_message = error_messages[i % len(error_messages)]

            await ocr_job_model.create(
                status=status,
                error_message=error_message,
                created_at=datetime.now() - timedelta(days=i // 5, hours=i % 24),
            )
            ocr_jobs_created += 1
        except Exception as e:
            print(f"OCR Job {i} 생성 실패: {e}")
    return ocr_jobs_created


if __name__ == "__main__":
    asyncio.run(create_sample_data())
