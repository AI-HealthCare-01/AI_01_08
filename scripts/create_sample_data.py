#!/usr/bin/env python3
"""
대시보드 테스트용 샘플 데이터 생성 스크립트
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, date
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tortoise import Tortoise
from app.core.config import get_settings
from app.models.users import User, Gender
from app.models.guides import Guide
from app.models.documents import OcrJob
from app.models.patients import Patient


async def create_sample_data():
    """샘플 데이터 생성"""
    settings = get_settings()
    
    # 데이터베이스 연결
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["app.models"]},
    )
    
    print("🔄 샘플 데이터 생성 중...")
    
    # 1. 사용자 데이터 생성
    users_created = 0
    for i in range(10):
        try:
            user = await User.create(
                email=f"test_user_{i}@example.com",
                name=f"테스트사용자{i}",
                gender=Gender.MALE if i % 2 == 0 else Gender.FEMALE,
                birthday=date(1990, 1, 1) + timedelta(days=i*30),
                phone_number=f"010-0000-{1000+i}",
                nickname=f"닉네임{i}",
                is_active=True,
                created_at=datetime.now() - timedelta(days=i),
            )
            users_created += 1
        except Exception as e:
            print(f"사용자 {i} 생성 실패: {e}")
    
    print(f"✅ 사용자 {users_created}명 생성 완료")
    
    # 2. 환자 데이터 생성
    patients_created = 0
    for i in range(5):
        try:
            patient = await Patient.create(
                name=f"환자{i}",
                gender=Gender.MALE if i % 2 == 0 else Gender.FEMALE,
                birthday=date(1980, 1, 1) + timedelta(days=i*60),
                phone_number=f"010-1111-{2000+i}",
                created_at=datetime.now() - timedelta(days=i*2),
            )
            patients_created += 1
        except Exception as e:
            print(f"환자 {i} 생성 실패: {e}")
    
    print(f"✅ 환자 {patients_created}명 생성 완료")
    
    # 3. 가이드 데이터 생성 (최근 30일간)
    patients = await Patient.all()
    guides_created = 0
    
    for i in range(50):
        try:
            patient = patients[i % len(patients)] if patients else None
            if patient:
                guide = await Guide.create(
                    patient=patient,
                    status="completed" if i % 3 != 0 else "processing",
                    content=f"가이드 내용 {i}",
                    created_at=datetime.now() - timedelta(days=i//2, hours=i%24),
                )
                guides_created += 1
        except Exception as e:
            print(f"가이드 {i} 생성 실패: {e}")
    
    print(f"✅ 가이드 {guides_created}개 생성 완료")
    
    # 4. OCR Job 데이터 생성
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
                    "파일이 손상되었습니다"
                ]
                error_message = error_messages[i % len(error_messages)]
            
            ocr_job = await OcrJob.create(
                status=status,
                error_message=error_message,
                created_at=datetime.now() - timedelta(days=i//5, hours=i%24),
            )
            ocr_jobs_created += 1
        except Exception as e:
            print(f"OCR Job {i} 생성 실패: {e}")
    
    print(f"✅ OCR Job {ocr_jobs_created}개 생성 완료")
    
    # 데이터베이스 연결 종료
    await Tortoise.close_connections()
    
    print("🎉 샘플 데이터 생성 완료!")
    print(f"   - 사용자: {users_created}명")
    print(f"   - 환자: {patients_created}명") 
    print(f"   - 가이드: {guides_created}개")
    print(f"   - OCR Job: {ocr_jobs_created}개")


if __name__ == "__main__":
    asyncio.run(create_sample_data())